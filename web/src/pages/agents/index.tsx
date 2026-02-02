import { CardSineLineContainer } from '@/components/card-singleline-container';
import { EmptyCardType } from '@/components/empty/constant';
import { EmptyAppCard } from '@/components/empty/empty';
import ListFilterBar from '@/components/list-filter-bar';
import { RenameDialog } from '@/components/rename-dialog';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { RAGFlowPagination } from '@/components/ui/ragflow-pagination';
import { useNavigatePage } from '@/hooks/logic-hooks/navigate-hooks';
import { useFetchAgentListByPage } from '@/hooks/use-agent-request';
import { t } from 'i18next';
import { pick } from 'lodash';
import { Clipboard, ClipboardPlus, FileInput, Plus } from 'lucide-react';
import { useCallback, useEffect } from 'react';
import { useSearchParams } from 'umi';
import { AgentCard } from './agent-card';
import { CreateAgentDialog } from './create-agent-dialog';
import { useCreateAgentOrPipeline } from './hooks/use-create-agent';
import { useSelectFilters } from './hooks/use-selelct-filters';
import { UploadAgentDialog } from './upload-agent-dialog';
import { useHandleImportJsonFile } from './use-import-json';
import { useRenameAgent } from './use-rename-agent';

export default function Agents() {
  const {
    data,
    pagination,
    setPagination,
    searchString,
    handleInputChange,
    filterValue,
    handleFilterSubmit,
  } = useFetchAgentListByPage();
  const { navigateToAgentTemplates } = useNavigatePage();

  const {
    agentRenameLoading,
    initialAgentName,
    onAgentRenameOk,
    agentRenameVisible,
    hideAgentRenameModal,
    showAgentRenameModal,
  } = useRenameAgent();

  const {
    creatingVisible,
    hideCreatingModal,
    showCreatingModal,
    loading,
    handleCreateAgentOrPipeline,
  } = useCreateAgentOrPipeline();

  const {
    handleImportJson,
    fileUploadVisible,
    onFileUploadOk,
    hideFileUploadModal,
  } = useHandleImportJsonFile();

  const filters = useSelectFilters();

  const handlePageChange = useCallback(
    (page: number, pageSize?: number) => {
      setPagination({ page, pageSize });
    },
    [setPagination],
  );
  const [searchUrl, setSearchUrl] = useSearchParams();
  const isCreate = searchUrl.get('isCreate') === 'true';
  useEffect(() => {
    if (isCreate) {
      showCreatingModal();
      searchUrl.delete('isCreate');
      setSearchUrl(searchUrl);
    }
  }, [isCreate, showCreatingModal, searchUrl, setSearchUrl]);

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-10 w-full px-10 pt-8">
      {(!data?.length || data?.length <= 0) && !searchString ? (
        <div className="flex w-full items-center justify-center py-20">
          <EmptyAppCard
            showIcon
            size="large"
            className="w-[480px] p-14 bg-card border-border/50 shadow-sm"
            isSearch={!!searchString}
            type={EmptyCardType.Agent}
            onClick={() => showCreatingModal()}
          />
        </div>
      ) : (
        <>
          <ListFilterBar
            title={t('flow.agents')}
            searchString={searchString}
            onSearchChange={handleInputChange}
            icon="agents"
            filters={filters}
            onChange={handleFilterSubmit}
            value={filterValue}
          >
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button className="gradient-primary shadow-glow border-none">
                  <Plus className="mr-2 h-4 w-4" />
                  {t('flow.createGraph')}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent
                align="end"
                className="w-56 rounded-xl p-2 bg-popover/95 backdrop-blur-sm border-border/50 shadow-xl"
              >
                <DropdownMenuItem
                  className="rounded-lg gap-3 py-2.5 cursor-pointer"
                  onClick={showCreatingModal}
                >
                  <div className="p-1.5 rounded-md bg-primary/10 text-primary">
                    <Clipboard className="size-4" />
                  </div>
                  <span className="font-medium">
                    {t('flow.createFromBlank')}
                  </span>
                </DropdownMenuItem>
                <DropdownMenuItem
                  className="rounded-lg gap-3 py-2.5 cursor-pointer"
                  onClick={navigateToAgentTemplates}
                >
                  <div className="p-1.5 rounded-md bg-primary/10 text-primary">
                    <ClipboardPlus className="size-4" />
                  </div>
                  <span className="font-medium">
                    {t('flow.createFromTemplate')}
                  </span>
                </DropdownMenuItem>
                <DropdownMenuItem
                  className="rounded-lg gap-3 py-2.5 cursor-pointer"
                  onClick={handleImportJson}
                >
                  <div className="p-1.5 rounded-md bg-primary/10 text-primary">
                    <FileInput className="size-4" />
                  </div>
                  <span className="font-medium">
                    {t('flow.importJsonFile')}
                  </span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </ListFilterBar>
          {(!data?.length || data?.length <= 0) && searchString && (
            <div className="flex w-full items-center justify-center py-20">
              <EmptyAppCard
                showIcon
                size="large"
                className="w-[480px] p-14 bg-card border-border/50 shadow-sm"
                isSearch={!!searchString}
                type={EmptyCardType.Agent}
                onClick={() => showCreatingModal()}
              />
            </div>
          )}
          <div className="flex-1 overflow-auto">
            <CardSineLineContainer>
              {data.map((x) => {
                return (
                  <AgentCard
                    key={x.id}
                    data={x}
                    showAgentRenameModal={showAgentRenameModal}
                  ></AgentCard>
                );
              })}
            </CardSineLineContainer>
          </div>
          <div className="mt-8 flex justify-end">
            <RAGFlowPagination
              {...pick(pagination, 'current', 'pageSize')}
              total={pagination.total}
              onChange={handlePageChange}
            ></RAGFlowPagination>
          </div>
        </>
      )}
      {agentRenameVisible && (
        <RenameDialog
          hideModal={hideAgentRenameModal}
          onOk={onAgentRenameOk}
          initialName={initialAgentName}
          loading={agentRenameLoading}
        ></RenameDialog>
      )}
      {creatingVisible && (
        <CreateAgentDialog
          loading={loading}
          visible={creatingVisible}
          hideModal={hideCreatingModal}
          shouldChooseAgent
          onOk={handleCreateAgentOrPipeline}
        ></CreateAgentDialog>
      )}
      {fileUploadVisible && (
        <UploadAgentDialog
          hideModal={hideFileUploadModal}
          onOk={onFileUploadOk}
        ></UploadAgentDialog>
      )}
    </div>
  );
}
