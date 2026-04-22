import React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs) {
  return twMerge(clsx(inputs));
}

const StatCard = ({ label, value, icon: Icon, trend, color = 'primary' }) => {
  const colors = {
    primary: 'text-primary bg-primary/10 border-primary/20',
    success: 'text-success bg-success/10 border-success/20',
    warning: 'text-warning bg-warning/10 border-warning/20',
    danger: 'text-danger bg-danger/10 border-danger/20',
  };

  return (
    <div className="glass rounded-2xl p-6 card-hover group">
      <div className="flex items-center justify-between mb-4">
        <div className={cn("w-12 h-12 rounded-xl flex items-center justify-center border", colors[color])}>
          <Icon className="w-6 h-6" />
        </div>
        {trend && (
          <span className={cn(
            "text-sm font-medium px-2 py-1 rounded-full",
            trend > 0 ? "bg-success/10 text-success" : "bg-danger/10 text-danger"
          )}>
            {trend > 0 ? '+' : ''}{trend}%
          </span>
        )}
      </div>
      <div>
        <p className="text-secondary text-sm font-medium mb-1">{label}</p>
        <h3 className="text-2xl font-bold tracking-tight">{value}</h3>
      </div>
    </div>
  );
};

export default StatCard;
