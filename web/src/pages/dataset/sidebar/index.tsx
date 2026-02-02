import { IconFontFill } from '@/components/icon-font';
import { RAGFlowAvatar } from '@/components/ragflow-avatar';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  useFetchKnowledgeBaseConfiguration,
  useFetchKnowledgeGraph,
} from '@/hooks/use-knowledge-request';
import { cn, formatBytes } from '@/lib/utils';
import { Routes } from '@/routes';
import { formatPureDate } from '@/utils/date';
import { isEmpty } from 'lodash';
import {
  ArrowLeft,
  Banknote,
  FileSearch2,
  FolderOpen,
  Logs,
} from 'lucide-react';
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocation, useNavigate } from 'umi';
import { useHandleMenuClick } from './hooks';

type PropType = {
  refreshCount?: number;
};

export function SideBar({ refreshCount }: PropType) {
  const { pathname } = useLocation();
  const { handleMenuClick } = useHandleMenuClick();
  const { data } = useFetchKnowledgeBaseConfiguration({ refreshCount });
  const { data: routerData } = useFetchKnowledgeGraph();
  const { t } = useTranslation();
  const navigate = useNavigate();

  const items = useMemo(() => {
    const list = [
      {
        icon: FolderOpen,
        label: t(`knowledgeDetails.subbarFiles`),
        key: Routes.DatasetBase,
      },
      {
        icon: FileSearch2,
        label: t(`knowledgeDetails.testing`),
        key: Routes.DatasetTesting,
      },
      {
        icon: Logs,
        label: t(`knowledgeDetails.overview`),
        key: Routes.DataSetOverview,
      },
      {
        icon: Banknote,
        label: t(`knowledgeDetails.configuration`),
        key: Routes.DataSetSetting,
      },
    ];
    if (!isEmpty(routerData?.graph)) {
      list.push({
        //@ts-ignore
        icon: 'knowledgegraph',
        label: t(`knowledgeDetails.knowledgeGraph`),
        key: Routes.KnowledgeGraph,
      });
    }
    return list;
  }, [t, routerData]);

  return (
    <div className="relative flex flex-col h-screen border-r w-[260px] bg-sidebar border-sidebar-border transition-all duration-300">
      <div className="absolute left-0 top-0 bottom-0 w-1 gradient-border opacity-40" />

      {/* Return Section */}
      <div className="px-4 py-8">
        <Button
          variant="ghost"
          className="w-full justify-start gap-3 text-sidebar-foreground hover:bg-sidebar-accent hover:text-foreground group rounded-xl p-3 h-11"
          onClick={() => navigate(Routes.Datasets)}
        >
          <div className="p-2 rounded-lg bg-background/50 text-sidebar-foreground group-hover:scale-110 group-hover:text-primary transition-all duration-300 shadow-sm">
            <ArrowLeft className="size-4" />
          </div>
          <span className="text-sm font-semibold tracking-tight">Datasets</span>
        </Button>
      </div>

      {/* Header Profile Section */}
      <div className="px-4 pb-8 border-b border-sidebar-border/30">
        <div className="flex flex-col items-center gap-4 text-center">
          <div className="relative group">
            <div className="absolute -inset-1 bg-gradient-to-r from-primary to-accent-primary rounded-2xl blur opacity-25 group-hover:opacity-50 transition duration-1000 group-hover:duration-200" />
            <RAGFlowAvatar
              avatar={data.avatar}
              name={data.name}
              className="size-20 rounded-2xl border-2 border-background shadow-xl"
            />
          </div>
          <div className="space-y-1 w-full overflow-hidden px-2">
            <h3 className="text-lg font-bold tracking-tight text-foreground truncate">
              {data.name}
            </h3>
            <div className="flex items-center justify-center gap-2 text-[10px] uppercase tracking-wider font-bold text-muted-foreground/70">
              <span>
                {data.doc_num} {t('knowledgeDetails.files')}
              </span>
              <span className="size-1 rounded-full bg-border" />
              <span>{formatBytes(data.size)}</span>
            </div>
          </div>
        </div>
      </div>

      <ScrollArea className="flex-1 px-4 pt-6 font-medium">
        <div className="flex flex-col gap-1.5">
          {items.map((item, idx) => {
            const isActive =
              pathname === item.key ||
              (item.key === Routes.DatasetBase &&
                pathname === '/dataset/dataset');
            const Icon = item.icon;

            return (
              <div key={idx} className="relative group px-1">
                <div
                  className={cn(
                    'flex items-center gap-3 w-full px-3 py-2 rounded-xl transition-all duration-300 cursor-pointer group h-11',
                    isActive
                      ? 'bg-sidebar-accent/50 text-foreground shadow-[inset_0_1px_1px_0_rgba(255,255,255,0.05)]'
                      : 'text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-foreground',
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
                    {typeof Icon === 'string' ? (
                      <IconFontFill name={Icon} className="size-4" />
                    ) : (
                      <Icon size={18} />
                    )}
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
      </ScrollArea>

      <div className="p-6 border-t border-sidebar-border/50">
        <div className="flex flex-col gap-1 text-[10px] text-muted-foreground/50 tracking-wide font-mono">
          <span>{t('knowledgeDetails.created')}</span>
          <span className="text-muted-foreground/80">
            {formatPureDate(data.create_time)}
          </span>
        </div>
      </div>
    </div>
  );
}
