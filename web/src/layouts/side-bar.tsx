import { ScrollArea } from '@/components/ui/scroll-area';
import { useNavigateWithFromState } from '@/hooks/route-hook';
import { cn } from '@/lib/utils';
import { Routes } from '@/routes';
import {
  BotIcon,
  Cpu,
  File,
  House,
  Library,
  MessageSquareText,
  Search,
} from 'lucide-react';
import { useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocation } from 'umi';

export function SideBar() {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const navigate = useNavigateWithFromState();

  const tagsData = useMemo(
    () => [
      { path: Routes.Root, name: t('header.home'), icon: House },
      { path: Routes.Datasets, name: t('header.dataset'), icon: Library },
      { path: Routes.Chats, name: t('header.chat'), icon: MessageSquareText },
      { path: Routes.Searches, name: t('header.search'), icon: Search },
      { path: Routes.Agents, name: t('header.flow'), icon: BotIcon },
      { path: Routes.Memories, name: t('header.Memories'), icon: Cpu },
      { path: Routes.Files, name: t('header.fileManager'), icon: File },
    ],
    [t],
  );

  const currentPath = useMemo(() => {
    // Find specific matches first, excluding the root path "/"
    const specificMatch = tagsData
      .filter((x) => x.path !== Routes.Root)
      .find((x) => pathname.startsWith(x.path))?.path;

    if (specificMatch) {
      return specificMatch;
    }

    // Check base routes for detail pages
    if (pathname.startsWith(Routes.DatasetBase)) {
      return Routes.Datasets;
    } else if (
      pathname.startsWith(Routes.Chat) ||
      pathname.startsWith(Routes.ChatShare)
    ) {
      return Routes.Chats;
    } else if (
      pathname.startsWith(Routes.Search) ||
      pathname.startsWith(Routes.SearchShare)
    ) {
      return Routes.Searches;
    } else if (
      pathname.startsWith(Routes.Agent) ||
      pathname.startsWith(Routes.AgentTemplates)
    ) {
      return Routes.Agents;
    } else if (pathname.startsWith(Routes.Memory)) {
      return Routes.Memories;
    } else if (pathname.startsWith('/user-setting')) {
      return Routes.Root;
    }

    // Fallback to Home only if exactly at root or no other match
    return Routes.Root;
  }, [pathname, tagsData]);

  const handleLogoClick = useCallback(() => {
    navigate(Routes.Root);
  }, [navigate]);

  return (
    <div className="relative flex flex-col h-screen border-r w-[260px] bg-sidebar border-sidebar-border transition-all duration-300">
      {/* Gradient accent bar decorations */}
      <div className="absolute left-0 top-0 bottom-0 w-1 gradient-border opacity-40" />

      {/* Logo Section */}
      <div className="flex items-center gap-3 px-4 py-6">
        <div
          className="relative flex items-center justify-center w-10 h-10 rounded-xl gradient-primary shadow-glow cursor-pointer transition-transform hover:scale-105"
          onClick={handleLogoClick}
        >
          <Cpu className="size-6 text-white" />
        </div>
        <div
          className="flex flex-col leading-tight cursor-pointer"
          onClick={handleLogoClick}
        >
          <span className="text-lg font-bold text-foreground tracking-tight">
            NPT Cortex
          </span>
          <span className="text-[10px] text-muted-foreground uppercase tracking-widest font-semibold opacity-70">
            Enterprise AI Core
          </span>
        </div>
      </div>

      <ScrollArea className="flex-1 px-3">
        <div className="flex flex-col gap-2 mt-2">
          {tagsData.map((tag) => {
            const Icon = tag.icon;
            const isActive = currentPath === tag.path;

            return (
              <div key={tag.path}>
                <div
                  className={cn(
                    'flex items-center gap-3 w-full px-3 py-2 rounded-xl transition-all duration-300 cursor-pointer group relative',
                    isActive
                      ? 'bg-sidebar-accent/50 text-foreground'
                      : 'text-sidebar-foreground hover:bg-sidebar-accent hover:text-foreground',
                  )}
                  onClick={() => navigate(tag.path as Routes)}
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
                      isActive && 'text-foreground font-semibold',
                    )}
                  >
                    {tag.name}
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
    </div>
  );
}
