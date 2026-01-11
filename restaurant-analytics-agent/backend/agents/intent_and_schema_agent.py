"""
Intent and Schema Analyzer Agent (Merged)
Combines intent classification and schema analysis into a single LLM call
to reduce latency while maintaining quality.
"""

import json
import logging
import re
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate

from ..config.schema_knowledge import SCHEMA_KNOWLEDGE, get_schema_summary
from ..config.settings import get_settings
from ..models.state import AgentState, ExtractedEntities, JoinInfo, QueryIntent, TimeRange
from ..utils.llm_factory import create_llm

logger = logging.getLogger(__name__)

# Rule-based intent detection patterns
INTENT_PATTERNS = {
    QueryIntent.SALES_ANALYSIS: [
        r"\b(total|revenue|sales|income|earnings|money|dollars?|amount)\b",
        r"\b(sell|sold|made|generated)\b",
        r"\b(gross|net)\s+(revenue|sales|income)\b",
        r"\bhow\s+much\b",
        r"\bwhat\s+(was|were|is)\s+(the\s+)?(total|revenue|sales)\b",
    ],
    QueryIntent.PRODUCT_ANALYSIS: [
        r"\b(top|best|worst|most|least|popular|selling|sold)\s+(products?|items?|dishes?|food)\b",
        r"\b(products?|items?)\s+(by|ranked|ranking|performance)\b",
        r"\b(which|what)\s+(products?|items?)\b",
        r"\b(product|item)\s+(sales|performance|analysis|breakdown)\b",
        r"\b(top|best)\s+\d+\s+(products?|items?)\b",
        r"\b(compare|comparison)\s+(sales|revenue|performance)\s+(of|for)\b",  # "Compare sales of X and Y"
        r"\b(sales|revenue)\s+(of|for)\s+.*\s+(and|vs|versus)\s+.*\b",  # "sales of X and Y"
    ],
    QueryIntent.LOCATION_COMPARISON: [
        r"\b(compare|comparison|vs|versus|between)\s+(locations?|stores?|restaurants?)\b",
        r"\b(locations?|stores?|restaurants?)\s+(compare|comparison|vs|versus)\b",
        r"\b(by|across|per)\s+(location|store|restaurant)\b",
        r"\b(which|what)\s+(location|store|restaurant)\b",
        r"\b(location|store|restaurant)\s+(performance|revenue|sales|comparison)\b",
    ],
    QueryIntent.TIME_SERIES: [
        r"\b(daily|hourly|weekly|monthly|day|hour|week|month)\s+(sales|revenue|trend|pattern|analysis)\b",
        r"\b(sales|revenue|trend|pattern)\s+(over|by|per)\s+(time|day|hour|week|month|date)\b",
        r"\b(trend|pattern|over\s+time|time\s+series)\b",
        r"\b(busiest|peak|slow)\s+(hours?|times?|periods?)\b",
        r"\b(how|what)\s+(did|does)\s+(sales|revenue)\s+(change|vary|trend)\b",
        r"\bgraph|chart|plot\s+(sales|revenue)\b",
    ],
    QueryIntent.PAYMENT_ANALYSIS: [
        r"\b(payment|payments?)\s+(method|type|breakdown|analysis|comparison)\b",
        r"\b(credit|debit|cash|card|payment)\s+(vs|versus|breakdown|comparison)\b",
        r"\b(which|what)\s+(payment|payments?)\s+(method|type)\b",
        r"\b(most|least)\s+(used|popular)\s+(payment|payments?)\b",
        r"\b(tip|tips?|tipping)\s+(analysis|breakdown|by|per)\b",
    ],
    QueryIntent.ORDER_TYPE_ANALYSIS: [
        r"\b(order\s+type|order\s+types?)\s+(analysis|comparison|breakdown|performance)\b",
        r"\b(dine\s*[-]?in|delivery|takeout|pickup|carry\s*out)\s+(vs|versus|comparison|breakdown)\b",
        r"\b(compare|comparison)\s+(dine\s*[-]?in|delivery|takeout|pickup)\b",
        r"\b(which|what)\s+(order\s+type|order\s+types?)\b",
    ],
    QueryIntent.SOURCE_COMPARISON: [
        r"\b(source|sources?|system|systems?)\s+(comparison|compare|breakdown|analysis)\b",
        r"\b(toast|doordash|square)\s+(vs|versus|comparison|breakdown)\b",
        r"\b(compare|comparison)\s+(toast|doordash|square)\b",
        r"\b(which|what)\s+(source|system)\s+(generates?|has)\b",
        r"\b(revenue|sales)\s+(by|from|per)\s+(source|system)\b",
    ],
    QueryIntent.CATEGORY_ANALYSIS: [
        r"\b(category|categories|catgories?)\s+(sales|revenue|performance|analysis|breakdown|comparison|selling|rank|ranking)\b",  # Handle typo "catgories"
        r"\b(sales|revenue|performance|selling)\s+(by|per|across|of|for)\s+(category|categories|catgories?)\b",
        r"\b(which|what)\s+(category|categories|catgories?)\b",
        r"\b(top|best|worst|highest|lowest)\s+(selling\s+)?(category|categories|catgories?)\b",
        r"\b(top|best|worst)\s+(category|categories|catgories?)\b",
        r"\b(category|categories|catgories?)\s+(performance|sales|revenue|breakdown)\b",
        r"\b(compare|comparison)\s+(categories?|catgories?)\b",
        # Direct category mentions (boost score when specific categories are mentioned)
        r"\b(burgers|sides|beverages|sandwiches|breakfast|salads|entrees|appetizers|cocktails|steaks|alcohol|wraps|seafood|pasta|desserts|coffee)\b",
    ],
    QueryIntent.PERFORMANCE_METRICS: [
        r"\b(average|avg|mean|median)\s+(order\s+value|aov|revenue|sales)\b",
        r"\b(kpi|key\s+performance|metrics?|benchmark)\b",
        r"\b(performance|metrics?|kpi)\s+(by|per|across)\b",
        r"\b(how\s+well|performance)\s+(are|is)\b",
    ],
    QueryIntent.CUSTOMER_ANALYSIS: [
        r"\b(customer|customers?)\s+(analysis|behavior|patterns?|insights?)\b",
        r"\b(which|what)\s+(customer|customers?)\b",
        r"\b(customer|customers?)\s+(by|per|across)\b",
        r"\b(repeat|customer\s+retention|loyalty)\b",
    ],
}


def _extract_basic_entities(query: str) -> ExtractedEntities:
    """
    Extract basic entities from query using simple pattern matching.
    Used for rule-based fast path.
    """
    query_lower = query.lower()
    entities = ExtractedEntities(
        locations=[],
        products=[],
        categories=[],
        order_types=[],
        payment_types=[],
        sources=[],
        metrics=[],
        limit=None,
    )
    
    # Extract locations
    location_mappings = SCHEMA_KNOWLEDGE.get("entity_mappings", {}).get("locations", {})
    for loc_key, loc_value in location_mappings.items():
        if loc_key in query_lower:
            entities["locations"].append(loc_value)
    
    # Extract categories - use word boundaries to avoid partial matches
    category_mappings = SCHEMA_KNOWLEDGE.get("entity_mappings", {}).get("categories", {})
    # Sort by length (longest first) to match "breakfast burrito" before just "breakfast"
    sorted_categories = sorted(category_mappings.items(), key=lambda x: len(x[0]), reverse=True)
    for cat_key, cat_value in sorted_categories:
        # Use word boundary matching to avoid partial matches (e.g., "burger" in "hamburger")
        pattern = r"\b" + re.escape(cat_key) + r"\b"
        if re.search(pattern, query_lower, re.IGNORECASE):
            # Avoid duplicates
            if cat_value not in entities["categories"]:
                entities["categories"].append(cat_value)
    
    # Extract order types
    order_type_mappings = SCHEMA_KNOWLEDGE.get("entity_mappings", {}).get("order_types", {})
    for ot_key, ot_value in order_type_mappings.items():
        if ot_key in query_lower:
            entities["order_types"].append(ot_value)
    
    # Extract sources
    source_mappings = SCHEMA_KNOWLEDGE.get("entity_mappings", {}).get("sources", {})
    for src_key, src_value in source_mappings.items():
        if src_key in query_lower:
            entities["sources"].append(src_value)
    
    # Extract limit (top N)
    limit_match = re.search(r"\b(top|best|worst)\s+(\d+)\b", query_lower)
    if limit_match:
        entities["limit"] = int(limit_match.group(2))
    
    # Extract payment types
    payment_keywords = ["credit", "debit", "cash", "card", "apple pay", "google pay"]
    for payment in payment_keywords:
        if payment in query_lower:
            entities["payment_types"].append(payment.upper())
    
    return entities


def _extract_time_range(query: str) -> TimeRange:
    """
    Extract basic time range from query using pattern matching.
    """
    query_lower = query.lower()
    time_range = TimeRange()
    
    # Relative time patterns
    if re.search(r"\b(yesterday|yday)\b", query_lower):
        time_range["relative"] = "yesterday"
    elif re.search(r"\b(today)\b", query_lower):
        time_range["relative"] = "today"
    elif re.search(r"\b(last\s+week|past\s+week)\b", query_lower):
        time_range["relative"] = "last_week"
    elif re.search(r"\b(last\s+month|past\s+month)\b", query_lower):
        time_range["relative"] = "last_month"
    elif re.search(r"\b(daily|per\s+day|by\s+day)\b", query_lower):
        time_range["relative"] = "daily"
    elif re.search(r"\b(hourly|per\s+hour|by\s+hour)\b", query_lower):
        time_range["relative"] = "hourly"
    
    # Date patterns (January 1-4, 2025)
    date_match = re.search(r"(january|jan)\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s*[-–]\s*(\d{1,2}))?(?:\s*,\s*(\d{4}))?", query_lower)
    if date_match:
        # Simple extraction - LLM will handle complex date parsing
        pass
    
    return time_range


def rule_based_intent_detection(query: str) -> Optional[tuple[QueryIntent, float]]:
    """
    Rule-based intent detection using keyword patterns.
    
    Returns (intent, confidence) if a match is found with high confidence,
    or None if no clear match (should fall back to LLM).
    
    Args:
        query: User query string
        
    Returns:
        Tuple of (QueryIntent, confidence) or None
    """
    query_lower = query.lower()
    
    # Count matches for each intent
    intent_scores: dict[QueryIntent, int] = {}
    
    for intent, patterns in INTENT_PATTERNS.items():
        score = 0
        for pattern in patterns:
            matches = len(re.findall(pattern, query_lower, re.IGNORECASE))
            score += matches
        
        if score > 0:
            intent_scores[intent] = score
    
    # Special boost for category analysis: if specific category names are mentioned
    # and category patterns matched, boost the score
    if QueryIntent.CATEGORY_ANALYSIS in intent_scores:
        category_names = [
            "burgers", "sides", "beverages", "sandwiches", "breakfast", "salads",
            "entrees", "appetizers", "cocktails", "steaks", "alcohol", "wraps",
            "seafood", "pasta", "desserts", "coffee"
        ]
        category_mentions = sum(1 for cat in category_names if re.search(r"\b" + re.escape(cat) + r"\b", query_lower))
        if category_mentions > 0:
            # Boost score by 1 for each category mentioned (up to +2)
            intent_scores[QueryIntent.CATEGORY_ANALYSIS] += min(2, category_mentions)
    
    if not intent_scores:
        return None
    
    # Find the intent with the highest score
    best_intent = max(intent_scores.items(), key=lambda x: x[1])
    intent, score = best_intent
    
    # Calculate confidence based on score and whether there's a clear winner
    max_score = max(intent_scores.values())
    second_best_score = sorted(intent_scores.values(), reverse=True)[1] if len(intent_scores) > 1 else 0
    
    # High confidence if:
    # 1. Score is >= 2 (multiple pattern matches)
    # 2. Score is at least 2x the second best (or no competition)
    if max_score >= 2 and (second_best_score == 0 or max_score >= 2 * second_best_score):
        # Base confidence 0.75 for score 2, increases with more matches
        confidence = min(0.95, 0.75 + (max_score - 2) * 0.08)
        logger.info(f"Rule-based intent detection: {intent.value} (confidence: {confidence:.2f}, score: {max_score})")
        return (intent, confidence)
    elif max_score >= 1:
        # For score 1: boost confidence if it's a clear winner (no tie)
        # If there's a tie (multiple intents with same score), use lower confidence
        if second_best_score == 0:
            # Clear winner with score 1 - give it higher confidence
            confidence = 0.75
            logger.info(f"Rule-based intent detection: {intent.value} (confidence: {confidence:.2f}, score: {max_score}, clear winner)")
            return (intent, confidence)
        else:
            # Tie or close competition - use lower confidence, let LLM decide
            confidence = 0.6
            logger.info(f"Rule-based intent detection: {intent.value} (confidence: {confidence:.2f}, score: {max_score}) - tie/competition, may need LLM confirmation")
            return (intent, confidence)
    
    return None


# Combined prompt for intent classification and schema analysis
INTENT_AND_SCHEMA_PROMPT = """Analyze restaurant data query. Extract intent, entities, time range, AND determine required tables/columns.

=== PART 1: Intent & Entity Extraction ===
Intents: sales_analysis, product_analysis, location_comparison, time_series, payment_analysis, order_type_analysis, source_comparison, performance_metrics, category_analysis, customer_analysis
Entities: locations, products, categories, order_types, payment_types, sources, metrics, limit
Time: Relative or explicit. 
**CRITICAL: Database ONLY contains data from January 1-4, 2025 (2025-01-01 to 2025-01-04).**
When user asks for "yesterday", "today", "last week", etc., extract the relative term but note the data limitation.

Entity Mappings: {entity_mappings}

=== PART 2: Schema Analysis ===
Schema: {schema_summary}

QUICK GUIDE: Use mv_* views for analytics (10-50x faster, DOLLARS). Use base tables only for individual records. Views need no joins or division.

=== Query ===
Query: {user_query}
Context: {conversation_history}

Return JSON only:
{{
    "intent": "<intent_type>",
    "confidence": <0.0-1.0>,
    "entities": {{"locations": [], "products": [], "categories": [], "order_types": [], "payment_types": [], "sources": [], "metrics": [], "limit": null}},
    "time_range": {{"start_date": null, "end_date": null, "relative": "<relative_or_null>"}},
    "needs_clarification": false,
    "clarification_question": "",
    "tables": ["table1", "table2"],  // REQUIRED: Must include at least one table/view. For analytics queries, use materialized views (mv_*)
    "columns": {{"table": ["col1", "col2"]}},  // REQUIRED: Must include columns for each table
    "joins": [{{"from_table": "t1", "to_table": "t2", "join_condition": "t1.id=t2.id", "join_type": "LEFT JOIN"}}],  // Usually empty for materialized views
    "considerations": ["notes"],
    "use_views": true/false,  // true for materialized views, false for base tables
    "reasoning": "brief explanation"
}}

Set needs_clarification=true if vague, ambiguous, missing info, or confidence < 0.6.
CRITICAL: Always return at least one table in the "tables" array. For time series queries, use mv_daily_sales_summary or mv_hourly_sales_pattern.
"""


def intent_and_schema_agent(state: AgentState) -> AgentState:
    """
    Combined intent classification and schema analysis.
    
    Uses rule-based detection for fast path on common queries,
    falls back to LLM for complex/ambiguous queries.
    """
    logger.info(f"Intent and schema agent processing: {state.get('user_query', '')[:100]}...")

    # Track this agent in the trace
    agent_trace = state.get("agent_trace", [])
    agent_trace.append("intent_and_schema")

    user_query = state.get("user_query", "")
    
    # Try rule-based intent detection first (fast path)
    rule_result = rule_based_intent_detection(user_query)
    
    if rule_result and rule_result[1] >= 0.75:
        # High confidence rule-based match - use fast path
        intent, confidence = rule_result
        logger.info(f"Using rule-based intent detection (fast path): {intent.value} (confidence: {confidence:.2f})")
        
        # Extract basic entities and time range
        entities = _extract_basic_entities(user_query)
        time_range = _extract_time_range(user_query)
        
        # Use fallback schema analysis which is already intent-aware
        state["query_intent"] = intent
        state["intent_confidence"] = confidence
        state["entities_extracted"] = entities
        state["time_range"] = time_range
        state["needs_clarification"] = False
        state["clarification_question"] = ""
        
        # Use fallback schema analysis (it's already optimized for each intent)
        state = _fallback_schema_analysis(state)
        state["agent_trace"] = agent_trace
        
        logger.info(
            f"Rule-based classification complete: {intent.value} (confidence: {confidence:.2f}) | "
            f"Entities: {len(entities.get('locations', []))} locations, {len(entities.get('categories', []))} categories | "
            f"Schema: {len(state.get('relevant_tables', []))} tables, use_views={state.get('use_views', False)}"
        )
        
        return state
    
    # Medium/low confidence or no match - use LLM (original behavior)
    if rule_result:
        logger.info(f"Rule-based detection found {rule_result[0].value} but confidence ({rule_result[1]:.2f}) too low, using LLM")
    else:
        logger.info("No rule-based match found, using LLM for intent and schema analysis")

    try:
        settings = get_settings()

        # Initialize LLM with parameters suitable for both tasks
        # NOTE: Reasoning disabled for performance - classification doesn't need reasoning
        llm = create_llm(
            temperature=0.1,  # Low temperature for consistent classification
            top_p=1,
            max_tokens=768,  # Increased for combined output
            reasoning_budget=None,  # Disabled for performance (50-70% faster)
            enable_thinking=False,  # Disabled for performance
        )

        # Create prompt
        prompt = ChatPromptTemplate.from_template(INTENT_AND_SCHEMA_PROMPT)

        # Format entity mappings for context (compact format, no indentation)
        entity_mappings = json.dumps(SCHEMA_KNOWLEDGE.get("entity_mappings", {}), separators=(',', ':'))

        # Get compact schema summary (optimized for performance)
        schema_summary = get_schema_summary()

        # Format conversation history
        history = state.get("conversation_history", [])
        history_str = (
            "\n".join(
                [
                    f"{msg.get('role', 'user')}: {msg.get('content', '')}"
                    for msg in history[-3:]  # Last 3 messages for context
                ]
            )
            if history
            else "None"
        )

        # Create chain and invoke
        chain = prompt | llm

        response = chain.invoke(
            {
                "user_query": state.get("user_query", ""),
                "entity_mappings": entity_mappings,
                "schema_summary": schema_summary,
                "conversation_history": history_str,
            }
        )

        # Parse response
        response_text = response.content.strip()

        # Extract JSON from response (handle markdown code blocks)
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        result = json.loads(response_text)

        # === PART 1: Process Intent & Entities ===
        # Map intent string to enum
        intent_str = result.get("intent", "unknown")
        try:
            query_intent = QueryIntent(intent_str)
        except ValueError:
            query_intent = QueryIntent.UNKNOWN

        # Extract entities with validation
        entities = result.get("entities", {})
        extracted_entities = ExtractedEntities(
            locations=_normalize_locations(entities.get("locations", [])),
            products=entities.get("products", []),
            categories=_normalize_categories(entities.get("categories", [])),
            order_types=_normalize_order_types(entities.get("order_types", [])),
            payment_types=_normalize_payment_types(entities.get("payment_types", [])),
            sources=_normalize_sources(entities.get("sources", [])),
            metrics=entities.get("metrics", []),
            limit=entities.get("limit"),
        )

        # Extract time range
        time_range_data = result.get("time_range", {})
        time_range = TimeRange(
            start_date=time_range_data.get("start_date"),
            end_date=time_range_data.get("end_date"),
            relative=time_range_data.get("relative"),
        )

        # Update state with intent/entities
        confidence = result.get("confidence", 0.0)
        needs_clarification = result.get("needs_clarification", False) or confidence < 0.6

        state["query_intent"] = query_intent
        state["intent_confidence"] = confidence
        state["entities_extracted"] = extracted_entities
        state["time_range"] = time_range
        state["needs_clarification"] = needs_clarification
        state["clarification_question"] = result.get("clarification_question", "")

        # === PART 2: Process Schema Analysis ===
        tables = result.get("tables", [])
        columns = result.get("columns", {})

        # If LLM returned empty tables, use fallback
        if not tables or len(tables) == 0:
            logger.warning(
                f"LLM returned empty tables list for query '{state.get('user_query', '')[:50]}...', "
                f"using fallback schema analysis. Intent: {query_intent}"
            )
            state = _fallback_schema_analysis(state)
            state["agent_trace"] = agent_trace
            return state

        state["relevant_tables"] = tables
        state["relevant_columns"] = columns

        # Parse joins
        joins = []
        for join_data in result.get("joins", []):
            joins.append(
                JoinInfo(
                    from_table=join_data.get("from_table", ""),
                    to_table=join_data.get("to_table", ""),
                    join_condition=join_data.get("join_condition", ""),
                    join_type=join_data.get("join_type", "LEFT JOIN"),
                )
            )
        state["required_joins"] = joins

        state["schema_considerations"] = result.get("considerations", [])
        state["use_views"] = result.get("use_views", False)
        state["agent_trace"] = agent_trace

        logger.info(
            f"Intent classified: {query_intent.value} (confidence: {confidence:.2f}, needs_clarification: {needs_clarification}) | "
            f"Schema: {len(tables)} tables, {len(joins)} joins, use_views={state['use_views']}"
        )

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response: {e}")
        state["query_intent"] = QueryIntent.UNKNOWN
        state["intent_confidence"] = 0.0
        state["needs_clarification"] = True
        state["clarification_question"] = (
            "I couldn't understand your query. Could you please rephrase it?"
        )
        # Use fallback for schema
        state = _fallback_schema_analysis(state)
        state["agent_trace"] = agent_trace

    except Exception as e:
        logger.error(f"Intent and schema agent error: {e}")
        error_msg = str(e)
        
        # Check for API errors (403, 401, etc.)
        if "403" in error_msg or "Forbidden" in error_msg:
            state["clarification_question"] = (
                "API access denied. Please check your API key and account credits. "
                "If using Grok, ensure your account has available credits."
            )
        elif "401" in error_msg or "Unauthorized" in error_msg:
            state["clarification_question"] = (
                "API authentication failed. Please check your API key configuration."
            )
        else:
            state["clarification_question"] = (
                "An error occurred while processing your query. Please try again."
            )
        
        state["query_intent"] = QueryIntent.UNKNOWN
        state["intent_confidence"] = 0.0
        state["needs_clarification"] = True
        # Use fallback for schema
        state = _fallback_schema_analysis(state)
        state["agent_trace"] = agent_trace

    return state


def _fallback_schema_analysis(state: AgentState) -> AgentState:
    """
    Fallback schema analysis when LLM fails.
    Uses heuristics based on query intent AND query text.
    """
    intent = state.get("query_intent", QueryIntent.UNKNOWN)
    query = state.get("user_query", "").lower()

    # Check for keywords that indicate base table usage
    needs_base_tables = any(
        keyword in query
        for keyword in [
            "order details",
            "individual order",
            "list orders",
            "show orders",
            "specific order",
            "order #",
            "order number",
            "items in",
            "line items",
            "payment details",
            "card brand",
            "card type",
            "tip per",
            "server",
            "employee",
            "customer name",
            "refund",
            "modifier",
            "special instruction",
            "notes",
        ]
    )

    # Default mappings based on intent (prefer materialized views)
    intent_to_tables = {
        QueryIntent.SALES_ANALYSIS: {
            "tables": (
                ["mv_daily_sales_summary"]  # Use materialized view
                if not needs_base_tables
                else ["unified_orders", "unified_locations"]
            ),
            "columns": (
                {
                    "mv_daily_sales_summary": [
                        "order_date",
                        "location_code",
                        "location_name",
                        "total_revenue",
                        "net_revenue",
                        "order_count",
                    ]
                }
                if not needs_base_tables
                else {"unified_orders": ["order_id", "order_date", "total_cents", "voided"]}
            ),
            "use_views": not needs_base_tables,
        },
        QueryIntent.PRODUCT_ANALYSIS: {
            "tables": (
                ["mv_product_sales_summary"]  # Use materialized view
                if not needs_base_tables
                else ["unified_order_items", "unified_products"]
            ),
            "columns": (
                {
                    "mv_product_sales_summary": [
                        "product",
                        "category_name",
                        "total_quantity_sold",
                        "total_revenue",
                        "order_count",
                    ]
                }
                if not needs_base_tables
                else {"unified_order_items": ["product_name", "quantity", "total_price_cents"]}
            ),
            "use_views": not needs_base_tables,
        },
        QueryIntent.LOCATION_COMPARISON: {
            "tables": ["mv_location_performance", "mv_daily_sales_summary"],  # Prefer materialized views
            "columns": {
                "mv_location_performance": ["location_code", "location_name", "total_revenue", "order_count", "avg_order_value"],
                "mv_daily_sales_summary": ["location_code", "location_name", "total_revenue", "order_count"]
            },
            "use_views": True,
        },
        QueryIntent.TIME_SERIES: {
            "tables": (
                ["mv_daily_sales_summary"] if "hour" not in query else ["mv_hourly_sales_pattern"]  # Use materialized views
            ),
            "columns": {
                "mv_daily_sales_summary": ["order_date", "total_revenue", "order_count", "location_code"],
                "mv_hourly_sales_pattern": ["order_date", "order_hour", "total_revenue", "order_count", "location_code"]
            },
            "use_views": True,
        },
        QueryIntent.PAYMENT_ANALYSIS: {
            "tables": (
                ["mv_payment_methods_by_source"]  # Use materialized view
                if any(
                    keyword in query
                    for keyword in [
                        "most used",
                        "payment method",
                        "payment methods",
                        "compare payment",
                        "payment breakdown",
                        "top payment",
                    ]
                )
                else ["unified_payments", "unified_orders"]
            ),
            "columns": (
                {
                    "mv_payment_methods_by_source": [
                        "payment_type",
                        "source_system",
                        "transaction_count",
                        "total_amount",
                    ]
                }
                if any(
                    keyword in query
                    for keyword in [
                        "most used",
                        "payment method",
                        "payment methods",
                        "compare payment",
                        "payment breakdown",
                        "top payment",
                    ]
                )
                else {
                    "unified_payments": ["payment_type", "card_brand", "amount_cents", "tip_cents"],
                    "unified_orders": ["order_id", "voided"],
                }
            ),
            "use_views": any(
                keyword in query
                for keyword in [
                    "most used",
                    "payment method",
                    "payment methods",
                    "compare payment",
                    "payment breakdown",
                    "top payment",
                ]
            ),
        },
        QueryIntent.ORDER_TYPE_ANALYSIS: {
            "tables": ["mv_order_type_performance"],  # Use materialized view
            "columns": {
                "mv_order_type_performance": [
                    "order_type",
                    "source_system",
                    "location_code",
                    "order_count",
                    "net_revenue",
                    "gross_revenue",
                    "avg_order_value",
                ]
            },
            "use_views": True,
        },
        QueryIntent.CATEGORY_ANALYSIS: {
            "tables": ["mv_category_sales_summary"],  # Use materialized view
            "columns": {
                "mv_category_sales_summary": [
                    "category_name",
                    "total_revenue",
                    "total_quantity_sold",
                    "product_count",
                ]
            },
            "use_views": True,
        },
    }

    config = intent_to_tables.get(
        intent,
        {
            "tables": ["mv_daily_sales_summary"],  # Default to materialized view
            "columns": {"mv_daily_sales_summary": ["order_date", "total_revenue", "order_count", "location_code"]},
            "use_views": True,
        },
    )

    state["relevant_tables"] = config["tables"]
    state["relevant_columns"] = config["columns"]
    state["required_joins"] = []
    state["schema_considerations"] = [
        "Using fallback schema analysis",
        "Views already have values in dollars",
        "Filter voided = FALSE for base order tables",
    ]
    state["use_views"] = config["use_views"]

    return state


def _normalize_locations(locations: list) -> list:
    """Normalize location names to standard codes"""
    mappings = SCHEMA_KNOWLEDGE.get("entity_mappings", {}).get("locations", {})
    normalized = []
    for loc in locations:
        loc_lower = loc.lower()
        if loc_lower in mappings:
            normalized.append(mappings[loc_lower])
        else:
            normalized.append(loc.upper())
    return normalized


def _normalize_order_types(order_types: list) -> list:
    """Normalize order types to standard values"""
    mappings = SCHEMA_KNOWLEDGE.get("entity_mappings", {}).get("order_types", {})
    normalized = []
    for ot in order_types:
        ot_lower = ot.lower()
        if ot_lower in mappings:
            normalized.append(mappings[ot_lower])
        else:
            normalized.append(ot.upper())
    return normalized


def _normalize_payment_types(payment_types: list) -> list:
    """Normalize payment types to standard values"""
    mappings = SCHEMA_KNOWLEDGE.get("entity_mappings", {}).get("payment_types", {})
    normalized = []
    for pt in payment_types:
        pt_lower = pt.lower()
        if pt_lower in mappings:
            normalized.append(mappings[pt_lower])
        else:
            normalized.append(pt.upper())
    return normalized


def _normalize_sources(sources: list) -> list:
    """Normalize source system names"""
    mappings = SCHEMA_KNOWLEDGE.get("entity_mappings", {}).get("sources", {})
    normalized = []
    for src in sources:
        src_lower = src.lower()
        if src_lower in mappings:
            normalized.append(mappings[src_lower])
        else:
            normalized.append(src_lower)
    return normalized


def _normalize_categories(categories: list) -> list:
    """Normalize category names to exact values"""
    mappings = SCHEMA_KNOWLEDGE.get("entity_mappings", {}).get("categories", {})
    normalized = []
    for cat in categories:
        cat_lower = cat.lower()
        if cat_lower in mappings:
            normalized.append(mappings[cat_lower])
        else:
            # Try to match by checking if it's already in the exact format
            if cat in [
                "Burgers",
                "Sides",
                "Beverages",
                "Sandwiches",
                "Breakfast",
                "Salads",
                "Entrees",
                "Appetizers",
                "Cocktails",
                "Steaks",
                "Alcohol",
                "Wraps",
                "Seafood",
                "Pasta",
                "Desserts",
                "Coffee",
            ]:
                normalized.append(cat)
            else:
                normalized.append(cat)  # Keep original if no match
    return normalized

