import { CardSineLineContainer } from '@/components/card-singleline-container';
import { EmptyCardType } from '@/components/empty/constant';
import { EmptyAppCard } from '@/components/empty/empty';
import ListFilterBar from '@/components/list-filter-bar';
import { RenameDialog } from '@/components/rename-dialog';
import { Button } from '@/components/ui/button';
import { RAGFlowPagination } from '@/components/ui/ragflow-pagination';
import { useFetchNextKnowledgeListByPage } from '@/hooks/use-knowledge-request';
import { useQueryClient } from '@tanstack/react-query';
import { pick } from 'lodash';
import { Plus } from 'lucide-react';
import { useCallback, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'umi';
import { DatasetCard } from './dataset-card';
import { DatasetCreatingDialog } from './dataset-creating-dialog';
import { useSaveKnowledge } from './hooks';
import { useRenameDataset } from './use-rename-dataset';
import { useSelectOwners } from './use-select-owners';

export default function Datasets() {
  const { t } = useTranslation();
  const {
    visible,
    hideModal,
    showModal,
    onCreateOk,
    loading: creatingLoading,
  } = useSaveKnowledge();

  const {
    kbs,
    total,
    pagination,
    setPagination,
    handleInputChange,
    searchString,
    filterValue,
    handleFilterSubmit,
  } = useFetchNextKnowledgeListByPage();

  const owners = useSelectOwners();

  const {
    datasetRenameLoading,
    initialDatasetName,
    onDatasetRenameOk,
    datasetRenameVisible,
    hideDatasetRenameModal,
    showDatasetRenameModal,
  } = useRenameDataset();

  const handlePageChange = useCallback(
    (page: number, pageSize?: number) => {
      setPagination({ page, pageSize });
    },
    [setPagination],
  );
  const [searchUrl, setSearchUrl] = useSearchParams();
  const isCreate = searchUrl.get('isCreate') === 'true';
  const queryClient = useQueryClient();
  useEffect(() => {
    if (isCreate) {
      queryClient.invalidateQueries({ queryKey: ['tenantInfo'] });
      showModal();
      searchUrl.delete('isCreate');
      setSearchUrl(searchUrl);
    }
  }, [isCreate, showModal, searchUrl, setSearchUrl]);

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-10 w-full px-10 pt-8">
      {(!kbs?.length || kbs?.length <= 0) && !searchString ? (
        <div className="flex w-full items-center justify-center py-20">
          <EmptyAppCard
            showIcon
            size="large"
            className="w-[480px] p-14 bg-card border-border/50 shadow-sm"
            isSearch={!!searchString}
            type={EmptyCardType.Dataset}
            onClick={() => showModal()}
          />
        </div>
      ) : (
        <>
          <ListFilterBar
            title={t('header.dataset')}
            searchString={searchString}
            onSearchChange={handleInputChange}
            value={filterValue}
            filters={owners}
            onChange={handleFilterSubmit}
            icon={'datasets'}
          >
            <Button
              onClick={showModal}
              className="gradient-primary shadow-glow border-none"
            >
              <Plus className="size-4 mr-2" />
              {t('knowledgeList.createKnowledgeBase')}
            </Button>
          </ListFilterBar>
          {(!kbs?.length || kbs?.length <= 0) && searchString && (
            <div className="flex w-full items-center justify-center py-20">
              <EmptyAppCard
                showIcon
                size="large"
                className="w-[480px] p-14 bg-card border-border/50 shadow-sm"
                isSearch={!!searchString}
                type={EmptyCardType.Dataset}
                onClick={() => showModal()}
              />
            </div>
          )}
          <div className="flex-1">
            <CardSineLineContainer>
              {kbs.map((dataset) => {
                return (
                  <DatasetCard
                    dataset={dataset}
                    key={dataset.id}
                    showDatasetRenameModal={showDatasetRenameModal}
                  ></DatasetCard>
                );
              })}
            </CardSineLineContainer>
          </div>
          <div className="mt-8 flex justify-end">
            <RAGFlowPagination
              {...pick(pagination, 'current', 'pageSize')}
              total={total}
              onChange={handlePageChange}
            ></RAGFlowPagination>
          </div>
        </>
      )}
      {visible && (
        <DatasetCreatingDialog
          hideModal={hideModal}
          onOk={onCreateOk}
          loading={creatingLoading}
        ></DatasetCreatingDialog>
      )}
      {datasetRenameVisible && (
        <RenameDialog
          hideModal={hideDatasetRenameModal}
          onOk={onDatasetRenameOk}
          initialName={initialDatasetName}
          loading={datasetRenameLoading}
        ></RenameDialog>
      )}
    </div>
  );
}
