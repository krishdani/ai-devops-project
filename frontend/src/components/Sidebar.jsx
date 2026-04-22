import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Terminal, 
  AlertTriangle, 
  Cpu, 
  ShieldCheck,
  Settings
} from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs) {
  return twMerge(clsx(inputs));
}

const Sidebar = () => {
  const navItems = [
    { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/logs', icon: Terminal, label: 'Logs' },
    { to: '/alerts', icon: AlertTriangle, label: 'Alerts' },
    { to: '/analysis', icon: Cpu, label: 'AI Analysis' },
  ];

  return (
    <div className="w-64 h-screen glass border-r border-border fixed left-0 top-0 flex flex-col">
      <div className="p-6 flex items-center gap-3">
        <div className="w-10 h-10 bg-primary/20 rounded-xl flex items-center justify-center border border-primary/50 shadow-[0_0_15px_rgba(59,130,246,0.3)]">
          <ShieldCheck className="text-primary w-6 h-6" />
        </div>
        <h1 className="text-xl font-bold tracking-tight">
          DevOps<span className="text-primary">AI</span>
        </h1>
      </div>

      <nav className="flex-1 px-4 mt-4 space-y-2">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) => cn(
              "flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group",
              isActive 
                ? "bg-primary/10 text-primary border border-primary/20" 
                : "text-secondary hover:bg-white/5 hover:text-white"
            )}
          >
            <item.icon className="w-5 h-5" />
            <span className="font-medium">{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="p-4 border-t border-border">
        <button className="w-full flex items-center gap-3 px-4 py-3 text-secondary hover:bg-white/5 hover:text-white rounded-xl transition-all">
          <Settings className="w-5 h-5" />
          <span className="font-medium">Settings</span>
        </button>
      </div>
    </div>
  );
};

export default Sidebar;
