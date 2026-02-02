import { PageHeader } from '@/components/page-header';
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb';
import { Button } from '@/components/ui/button';
import { useSetModalState } from '@/hooks/common-hooks';
import { useNavigatePage } from '@/hooks/logic-hooks/navigate-hooks';
import { useFetchAgentTemplates, useSetAgent } from '@/hooks/use-agent-request';

import { CardContainer } from '@/components/card-container';
import { AgentCategory } from '@/constants/agent';
import { IFlowTemplate } from '@/interfaces/database/agent';
import { ArrowLeft } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { CreateAgentDialog } from './create-agent-dialog';
import { TemplateCard } from './template-card';
import { MenuItemKey, SideBar } from './template-sidebar';

export default function AgentTemplates() {
  const { navigateToAgents } = useNavigatePage();
  const { t } = useTranslation();
  const list = useFetchAgentTemplates();
  const { loading, setAgent } = useSetAgent();
  const [templateList, setTemplateList] = useState<IFlowTemplate[]>([]);
  const [selectMenuItem, setSelectMenuItem] = useState<string>(
    MenuItemKey.Recommended,
  );

  useEffect(() => {
    setTemplateList(list);
  }, [list]);

  const {
    visible: creatingVisible,
    hideModal: hideCreatingModal,
    showModal: showCreatingModal,
  } = useSetModalState();

  const [template, setTemplate] = useState<IFlowTemplate>();

  const showModal = useCallback(
    (record: IFlowTemplate) => {
      setTemplate(record);
      showCreatingModal();
    },
    [showCreatingModal],
  );

  const { navigateToAgent } = useNavigatePage();

  const handleOk = useCallback(
    async (payload: any) => {
      let dsl = template?.dsl;
      const canvasCategory = template?.canvas_category;

      const ret = await setAgent({
        title: payload.name,
        dsl,
        avatar: template?.avatar,
        canvas_category: canvasCategory,
      });

      if (ret?.code === 0) {
        hideCreatingModal();
        if (canvasCategory === AgentCategory.DataflowCanvas) {
          navigateToAgent(ret.data.id, AgentCategory.DataflowCanvas)();
        } else {
          navigateToAgent(ret.data.id)();
        }
      }
    },
    [
      hideCreatingModal,
      navigateToAgent,
      setAgent,
      template?.avatar,
      template?.canvas_category,
      template?.dsl,
    ],
  );
  const handleSiderBarChange = (keyword: string) => {
    setSelectMenuItem(keyword);
  };

  const tempListFilter = useMemo(() => {
    if (!selectMenuItem) {
      return templateList;
    }
    return templateList.filter(
      (item) =>
        item.canvas_type?.toLocaleLowerCase() ===
        selectMenuItem?.toLocaleLowerCase(),
    );
  }, [selectMenuItem, templateList]);

  return (
    <section className="h-full flex flex-col overflow-hidden bg-background">
      <PageHeader className="px-10 border-b border-border/40 bg-background/50 backdrop-blur-md">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            className="size-9 rounded-xl bg-background/50 text-sidebar-foreground hover:text-primary transition-all duration-300 shadow-sm border border-border/20 group"
            onClick={navigateToAgents}
          >
            <ArrowLeft className="size-4 group-hover:scale-110 transition-transform" />
          </Button>
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem>
                <BreadcrumbLink onClick={navigateToAgents}>
                  {t('flow.agent')}
                </BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbPage className="font-semibold text-primary">
                  {t('flow.createGraph')}
                </BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>
        </div>
      </PageHeader>
      <div className="flex flex-1 overflow-hidden">
        <SideBar
          change={handleSiderBarChange}
          selected={selectMenuItem}
        ></SideBar>

        <main className="flex-1 bg-background overflow-hidden relative">
          <CardContainer className="h-full overflow-auto p-10 pb-20">
            {tempListFilter?.map((x) => {
              return (
                <TemplateCard
                  key={x.id}
                  data={x}
                  showModal={showModal}
                ></TemplateCard>
              );
            })}
          </CardContainer>
          {creatingVisible && (
            <CreateAgentDialog
              loading={loading}
              visible={creatingVisible}
              hideModal={hideCreatingModal}
              onOk={handleOk}
            ></CreateAgentDialog>
          )}
        </main>
      </div>
    </section>
  );
}
