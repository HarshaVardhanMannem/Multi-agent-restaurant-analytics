# Example Natural Language Queries

These are examples of the types of queries your system should be able to handle. You don't need to support all of these—focus on building something functional first, then expand.

## Basic Queries (Start Here)
- "Show me total sales by location"
- "What was the revenue yesterday?"
- "List the top 10 selling items"

## Comparison Queries
- "Compare sales between Downtown and Airport"
- "Show me Downtown vs University revenue"
- "Which location had the highest sales?"

## Time-Based Queries
- "Show me sales for January 2nd"
- "What were hourly sales on the 3rd?"
- "Graph daily revenue for the first week"

## Product Analysis
- "What are the top selling items at the Mall?"
- "Show me beverage sales across all locations"
- "Which category generates the most revenue?"

## Channel Analysis
- "Compare delivery vs dine-in revenue"
- "How much came from DoorDash?"
- "Show me takeout orders by location"

## Advanced Queries (Stretch Goals)
- "Show me peak hours for each location"
- "What's the average order value by channel?"
- "Graph the trend of delivery orders over time"
- "Which payment methods are most popular?"

---

## Tips for Implementation

1. **Start simple**: Get basic aggregations working first
2. **Think about intent**: "sales" could mean revenue, order count, or items sold
3. **Handle ambiguity**: What if someone asks about "last week" but your data only has specific dates?
4. **Choose appropriate visualizations**: 
   - Comparisons → Bar charts
   - Trends over time → Line charts  
   - Part of whole → Pie charts
   - Detailed data → Tables
5. **Fail gracefully**: What happens when a query can't be answered?
