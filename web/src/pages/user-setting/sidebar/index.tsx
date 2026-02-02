import { IconFontFill } from '@/components/icon-font';
import ThemeToggle from '@/components/theme-toggle';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Domain } from '@/constants/common';
import { useSecondPathName } from '@/hooks/route-hook';
import { useLogout } from '@/hooks/use-login-request';
import { useFetchSystemVersion } from '@/hooks/use-user-setting-request';
import { cn } from '@/lib/utils';
import { Routes } from '@/routes';
import { TFunction } from 'i18next';
import {
  ArrowLeft,
  Banknote,
  Box,
  LogOut,
  Server,
  Unplug,
  User,
  Users,
} from 'lucide-react';
import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'umi';
import { useHandleMenuClick } from './hooks';

const menuItems = (t: TFunction) => [
  { icon: Server, label: t('setting.dataSources'), key: Routes.DataSource },
  { icon: Box, label: t('setting.model'), key: Routes.Model },
  { icon: Banknote, label: 'MCP', key: Routes.Mcp },
  { icon: Users, label: t('setting.team'), key: Routes.Team },
  { icon: User, label: t('setting.profile'), key: Routes.Profile },
  { icon: Unplug, label: t('setting.api'), key: Routes.Api },
  // {
  //   icon: MessageSquareQuote,
  //   label: 'Prompt Templates',
  //   key: Routes.Profile,
  // },
  // { icon: TextSearch, label: 'Retrieval Templates', key: Routes.Profile },
  // { icon: Cog, label: t('setting.system'), key: Routes.System },
  // { icon: Banknote, label: 'Plan', key: Routes.Plan },
];
export function SideBar() {
  const pathName = useSecondPathName();
  const { handleMenuClick, active } = useHandleMenuClick();
  const { version, fetchSystemVersion } = useFetchSystemVersion();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { logout } = useLogout();

  useEffect(() => {
    if (location.host !== Domain) {
      fetchSystemVersion();
    }
  }, [fetchSystemVersion]);

  return (
    <div className="relative flex flex-col h-screen border-r w-[260px] bg-sidebar border-sidebar-border transition-all duration-300">
      {/* Gradient accent bar decorations */}
      <div className="absolute left-0 top-0 bottom-0 w-1 gradient-border opacity-40" />

      {/* Return Section */}
      <div className="px-4 py-8">
        <Button
          variant="ghost"
          className="w-full justify-start gap-3 text-sidebar-foreground hover:bg-sidebar-accent hover:text-foreground group rounded-xl p-3"
          onClick={() => navigate(Routes.Root)}
        >
          <div className="p-2 rounded-lg bg-background/50 text-sidebar-foreground group-hover:scale-110 group-hover:text-primary transition-all duration-300 shadow-sm">
            <ArrowLeft className="size-4" />
          </div>
          <span className="text-sm font-semibold tracking-tight">
            Return Dashboard
          </span>
        </Button>
      </div>

      <ScrollArea className="flex-1 px-3">
        <div className="flex flex-col gap-2">
          {menuItems(t).map((item, idx) => {
            const isActive = active === item.key;
            const Icon = item.icon;

            return (
              <div key={idx} className="relative group">
                <div
                  className={cn(
                    'flex items-center gap-3 w-full px-3 py-2 rounded-xl transition-all duration-300 cursor-pointer group',
                    isActive
                      ? 'bg-sidebar-accent/50 text-foreground'
                      : 'text-sidebar-foreground hover:bg-sidebar-accent hover:text-foreground',
                  )}
                  onClick={handleMenuClick(item.key)}
                >
                  <div
                    className={cn(
                      'p-2 rounded-lg transition-all duration-300 flex items-center justify-center',
                      isActive
                        ? 'bg-primary text-primary-foreground shadow-glow'
                        : 'bg-background/50 text-sidebar-foreground group-hover:scale-110 group-hover:text-primary',
                    )}
                  >
                    {item.key === Routes.Mcp ? (
                      <IconFontFill name={'mcp'} className="size-4" />
                    ) : (
                      <Icon size={18} />
                    )}
                  </div>
                  <span
                    className={cn(
                      'text-sm font-medium transition-colors',
                      isActive && 'text-foreground font-semibold',
                    )}
                  >
                    {item.label}
                  </span>

                  {isActive && (
                    <div className="absolute left-0 w-1 h-6 bg-primary rounded-r-full" />
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </ScrollArea>

      <div className="p-4 mt-auto border-t border-sidebar-border/50">
        <div className="flex items-center justify-between mb-4 px-2">
          <span className="text-[10px] text-muted-foreground font-mono opacity-50 uppercase tracking-widest">
            {version}
          </span>
          <ThemeToggle />
        </div>
        <Button
          variant="ghost"
          className="w-full gap-3 text-destructive hover:text-destructive hover:bg-destructive/10 rounded-xl"
          onClick={() => logout()}
        >
          <LogOut className="size-4" />
          <span className="font-semibold">{t('setting.logout')}</span>
        </Button>
      </div>
    </div>
  );
}
