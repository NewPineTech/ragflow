import { cn } from '@/lib/utils';
import { t } from 'i18next';
import { lowerFirst } from 'lodash';
import {
  Box,
  ChartPie,
  Component,
  MessageCircleCode,
  PencilRuler,
  Route,
  Sparkle,
} from 'lucide-react';
export enum MenuItemKey {
  Recommended = 'Recommended',
  Agent = 'Agent',
  CustomerSupport = 'Customer Support',
  Marketing = 'Marketing',
  ConsumerApp = 'Consumer App',
  Pipeline = 'Ingestion Pipeline',
  Other = 'Other',
}
const menuItems = [
  {
    // section: 'All Templates',
    section: '',
    items: [
      {
        icon: Sparkle,
        label: t('flow.' + lowerFirst(MenuItemKey.Recommended)),
        key: MenuItemKey.Recommended,
      },
      {
        icon: Box,
        label: t('flow.' + lowerFirst(MenuItemKey.Agent)),
        key: MenuItemKey.Agent,
      },
      {
        icon: MessageCircleCode,
        label: t(
          'flow.' + lowerFirst(MenuItemKey.CustomerSupport).replace(' ', ''),
        ),
        key: MenuItemKey.CustomerSupport,
      },
      {
        icon: ChartPie,
        label: t('flow.' + lowerFirst(MenuItemKey.Marketing)),
        key: MenuItemKey.Marketing,
      },
      {
        icon: Component,
        label: t(
          'flow.' + lowerFirst(MenuItemKey.ConsumerApp.replace(' ', '')),
        ),
        key: MenuItemKey.ConsumerApp,
      },
      {
        icon: Route,
        label: t('flow.' + lowerFirst(MenuItemKey.Pipeline.replace(' ', ''))),
        key: MenuItemKey.Pipeline,
      },
      {
        icon: PencilRuler,
        label: t('flow.' + lowerFirst(MenuItemKey.Other)),
        key: MenuItemKey.Other,
      },
    ],
  },
];

export function SideBar({
  change,
  selected = MenuItemKey.Recommended,
}: {
  change: (keyword: string) => void;
  selected?: string;
}) {
  const handleMenuClick = (key: string) => {
    change(key);
  };

  return (
    <aside className="relative flex flex-col h-full border-r w-[260px] bg-sidebar border-sidebar-border transition-all duration-300">
      <div className="absolute left-0 top-0 bottom-0 w-1 gradient-border opacity-40" />

      <div className="flex-1 overflow-auto p-4 pt-6 font-medium">
        <div className="flex flex-col gap-1.5">
          {menuItems.map((section, idx) => (
            <div key={idx} className="space-y-1">
              {section.section && (
                <div className="px-3 pb-2 text-[10px] uppercase font-bold tracking-widest text-muted-foreground/50">
                  {section.section}
                </div>
              )}
              {section.items.map((item, itemIdx) => {
                const isActive = selected === item.key;
                const Icon = item.icon;

                return (
                  <div key={itemIdx} className="relative group px-1">
                    <div
                      className={cn(
                        'flex items-center gap-3 w-full px-3 py-2 rounded-xl transition-all duration-300 cursor-pointer group h-11',
                        isActive
                          ? 'bg-sidebar-accent/50 text-foreground shadow-[inset_0_1px_1px_0_rgba(255,255,255,0.05)]'
                          : 'text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-foreground',
                      )}
                      onClick={() => handleMenuClick(item.key)}
                    >
                      <div
                        className={cn(
                          'p-2 rounded-lg transition-all duration-300 flex items-center justify-center',
                          isActive
                            ? 'bg-primary text-primary-foreground shadow-glow'
                            : 'bg-background/50 text-sidebar-foreground group-hover:scale-110 group-hover:text-primary',
                        )}
                      >
                        <Icon size={18} />
                      </div>
                      <span
                        className={cn(
                          'text-sm font-medium transition-colors',
                          isActive
                            ? 'text-foreground font-semibold'
                            : 'opacity-80 group-hover:opacity-100',
                        )}
                      >
                        {item.label}
                      </span>

                      {isActive && (
                        <div className="absolute left-0 w-1 h-6 bg-primary rounded-r-full shadow-[0_0_8px_hsl(var(--primary))]" />
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
}
