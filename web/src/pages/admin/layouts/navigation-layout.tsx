import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { NavLink, Outlet, useNavigate } from 'umi';

import { useMutation, useQuery } from '@tanstack/react-query';

import {
  Cpu,
  LucideMonitor,
  LucideServerCrash,
  LucideSquareUserRound,
  LucideUserCog,
  LucideUserStar,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import { Routes } from '@/routes';
import { getSystemVersion, logout } from '@/services/admin-service';

import authorizationUtil from '@/utils/authorization-util';

import ThemeSwitch from '../components/theme-switch';
import { IS_ENTERPRISE } from '../utils';

const AdminNavigationLayout = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const { data: version } = useQuery({
    queryKey: ['admin/version'],
    queryFn: async () => (await getSystemVersion())?.data?.data?.version,
  });

  const navItems = useMemo(
    () => [
      {
        path: Routes.AdminServices,
        name: t('admin.serviceStatus'),
        icon: LucideServerCrash,
      },
      {
        path: Routes.AdminUserManagement,
        name: t('admin.userManagement'),
        icon: LucideUserCog,
      },
      ...(IS_ENTERPRISE
        ? [
            {
              path: Routes.AdminWhitelist,
              name: t('admin.registrationWhitelist'),
              icon: LucideUserStar,
            },
            {
              path: Routes.AdminRoles,
              name: t('admin.roles'),
              icon: LucideSquareUserRound,
            },
            {
              path: Routes.AdminMonitoring,
              name: t('admin.monitoring'),
              icon: LucideMonitor,
            },
          ]
        : []),
    ],
    [t],
  );

  const logoutMutation = useMutation({
    mutationKey: ['adminLogout'],
    mutationFn: async () => {
      await logout();
      authorizationUtil.removeAll();
      navigate(Routes.Admin);
    },
    retry: false,
  });

  return (
    <main className="w-screen h-screen flex flex-row bg-background dark:*:focus-visible:ring-white overflow-hidden">
      <aside className="relative flex flex-col h-full border-r w-[260px] bg-sidebar border-sidebar-border transition-all duration-300">
        <div className="absolute left-0 top-0 bottom-0 w-1 gradient-border opacity-40" />

        {/* Header */}
        <section className="flex items-center gap-3 px-6 h-[72px] shrink-0 border-b border-sidebar-border/50">
          <div className="flex items-center justify-center size-9 rounded-xl gradient-primary shadow-glow">
            <Cpu className="size-5 text-white" />
          </div>
          <div className="flex flex-col text-left">
            <span className="text-base font-bold tracking-tight text-foreground leading-none">
              NPT Cortex
            </span>
            <span className="text-[10px] text-muted-foreground font-semibold mt-1 tracking-wider uppercase opacity-80">
              Admin
            </span>
          </div>
        </section>

        {/* Navigation */}
        <div className="flex-1 overflow-auto p-4 font-medium">
          <ul className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <li key={item.path}>
                  <NavLink
                    to={item.path}
                    className={({ isActive }) =>
                      cn(
                        'relative group flex items-center gap-3 w-full px-3 py-2 rounded-xl transition-all duration-300 cursor-pointer h-11',
                        isActive
                          ? 'bg-sidebar-accent/50 text-foreground shadow-[inset_0_1px_1px_0_rgba(255,255,255,0.05)]'
                          : 'text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-foreground',
                      )
                    }
                  >
                    {({ isActive }) => (
                      <>
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
                          {item.name}
                        </span>

                        {isActive && (
                          <div className="absolute left-0 w-1 h-6 bg-primary rounded-r-full shadow-[0_0_8px_hsl(var(--primary))]" />
                        )}
                      </>
                    )}
                  </NavLink>
                </li>
              );
            })}
          </ul>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-sidebar-border/50 bg-background/20 backdrop-blur-sm">
          <div className="flex items-center justify-between mb-4 px-2">
            <span className="text-[10px] font-mono text-muted-foreground/60">
              v{version}
            </span>
            <ThemeSwitch />
          </div>

          <Button
            size="lg"
            variant="outline"
            className="w-full justify-start gap-3 h-11 rounded-xl border-border/50 bg-background hover:bg-destructive/10 hover:text-destructive hover:border-destructive/30 transition-all duration-300 shadow-sm"
            onClick={() => logoutMutation.mutate()}
          >
            <div className="p-1.5 rounded-lg bg-muted/50 group-hover:bg-destructive/20 transition-colors">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="lucide lucide-log-out"
              >
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                <polyline points="16 17 21 12 16 7" />
                <line x1="21" x2="9" y1="12" y2="12" />
              </svg>
            </div>
            <span className="font-semibold">{t('header.logout')}</span>
          </Button>
        </div>
      </aside>

      <section className="flex-1 h-full overflow-hidden bg-background">
        <ScrollArea className="h-full w-full">
          <Outlet />
        </ScrollArea>
      </section>
    </main>
  );
};

export default AdminNavigationLayout;
