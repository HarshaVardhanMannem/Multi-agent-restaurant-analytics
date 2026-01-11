'use client';

import { TrendingUp, TrendingDown, Minus, DollarSign, ShoppingCart, Users, Store, Clock, Package } from 'lucide-react';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: {
    value: number;
    label?: string;
  };
  icon?: 'dollar' | 'orders' | 'users' | 'store' | 'time' | 'items';
  format?: 'currency' | 'number' | 'percent';
  size?: 'sm' | 'md' | 'lg';
}

const iconMap = {
  dollar: DollarSign,
  orders: ShoppingCart,
  users: Users,
  store: Store,
  time: Clock,
  items: Package,
};

export default function MetricCard({
  title,
  value,
  subtitle,
  trend,
  icon = 'dollar',
  format = 'number',
  size = 'md',
}: MetricCardProps) {
  const IconComponent = iconMap[icon];

  const formatValue = (val: string | number): string => {
    if (typeof val === 'string') return val;
    
    switch (format) {
      case 'currency':
        return new Intl.NumberFormat('en-US', {
          style: 'currency',
          currency: 'USD',
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        }).format(val);
      case 'percent':
        return `${val.toFixed(1)}%`;
      case 'number':
      default:
        return new Intl.NumberFormat('en-US').format(val);
    }
  };

  const getTrendIcon = () => {
    if (!trend) return null;
    if (trend.value > 0) return <TrendingUp className="text-green-500" size={16} />;
    if (trend.value < 0) return <TrendingDown className="text-red-500" size={16} />;
    return <Minus className="text-gray-400" size={16} />;
  };

  const getTrendColor = () => {
    if (!trend) return '';
    if (trend.value > 0) return 'text-green-600';
    if (trend.value < 0) return 'text-red-600';
    return 'text-gray-500';
  };

  const sizeClasses = {
    sm: {
      container: 'p-4',
      icon: 'p-2',
      title: 'text-sm',
      value: 'text-2xl',
      subtitle: 'text-xs',
    },
    md: {
      container: 'p-5',
      icon: 'p-2.5',
      title: 'text-sm',
      value: 'text-3xl',
      subtitle: 'text-sm',
    },
    lg: {
      container: 'p-6',
      icon: 'p-3',
      title: 'text-base',
      value: 'text-4xl',
      subtitle: 'text-sm',
    },
  };

  const classes = sizeClasses[size];

  return (
    <div className={`bg-white rounded-2xl shadow-soft border border-gray-100 ${classes.container} hover:shadow-medium hover-lift transition-all duration-300`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className={`${classes.title} font-semibold text-gray-600 mb-2`}>{title}</p>
          <p className={`${classes.value} font-bold bg-gradient-to-br from-gray-900 to-gray-700 bg-clip-text text-transparent tracking-tight`}>
            {formatValue(value)}
          </p>
          {subtitle && (
            <p className={`${classes.subtitle} text-gray-500 mt-2`}>{subtitle}</p>
          )}
          {trend && (
            <div className={`flex items-center gap-1.5 mt-3 ${getTrendColor()}`}>
              {getTrendIcon()}
              <span className="text-sm font-semibold">
                {trend.value > 0 ? '+' : ''}{trend.value.toFixed(1)}%
              </span>
              {trend.label && (
                <span className="text-gray-400 text-sm ml-1">{trend.label}</span>
              )}
            </div>
          )}
        </div>
        <div className={`${classes.icon} bg-gradient-to-br from-primary-500 to-primary-600 rounded-xl shadow-sm`}>
          <IconComponent className="text-white" size={size === 'lg' ? 24 : size === 'md' ? 20 : 16} />
        </div>
      </div>
    </div>
  );
}
