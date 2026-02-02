import { RAGFlowAvatar } from '@/components/ragflow-avatar';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { IFlowTemplate } from '@/interfaces/database/agent';
import i18n from '@/locales/config';
import { useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
interface IProps {
  data: IFlowTemplate;
  isCreate?: boolean;
  showModal(record: IFlowTemplate): void;
}

export function TemplateCard({ data, showModal }: IProps) {
  const { t } = useTranslation();

  const handleClick = useCallback(() => {
    showModal(data);
  }, [data, showModal]);

  const language = useMemo(() => {
    const lng = i18n.language || 'en';
    return (lng.startsWith('zh') ? 'zh' : 'en') as 'en' | 'zh';
  }, []);

  return (
    <Card className="group relative border border-border/20 bg-card rounded-3xl overflow-hidden shadow-sm hover:shadow-xl transition-all duration-500 hover:-translate-y-1 min-h-40">
      <CardContent className="p-6">
        <div className="flex justify-start items-center gap-4 mb-5">
          <div className="p-1 rounded-2xl bg-background/50 border border-border/10 shadow-sm transition-transform duration-500 group-hover:scale-110">
            <RAGFlowAvatar
              className="size-10 rounded-xl"
              avatar={
                data.avatar ? data.avatar : 'https://github.com/shadcn.png'
              }
              name={data?.title[language] || 'CN'}
            />
          </div>
          <div
            className="text-lg font-bold tracking-tight text-foreground break-words hyphens-auto overflow-hidden"
            lang={language}
          >
            {data?.title[language]}
          </div>
        </div>
        <p
          className="text-sm leading-relaxed text-muted-foreground break-words hyphens-auto pb-16"
          lang={language}
        >
          {data?.description[language]}
        </p>

        <div className="absolute inset-0 bg-background/40 backdrop-blur-[2px] opacity-0 group-hover:opacity-100 transition-all duration-500 rounded-3xl px-6 pb-4 flex items-end">
          <Button
            className="w-full gradient-primary shadow-glow rounded-xl font-bold translate-y-2 group-hover:translate-y-0 transition-all duration-500 h-11"
            onClick={handleClick}
          >
            {t('flow.useTemplate')}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
