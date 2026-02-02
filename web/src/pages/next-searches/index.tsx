import { CardSineLineContainer } from '@/components/card-singleline-container';
import { EmptyCardType } from '@/components/empty/constant';
import { EmptyAppCard } from '@/components/empty/empty';
import ListFilterBar from '@/components/list-filter-bar';
import { RenameDialog } from '@/components/rename-dialog';
import { Button } from '@/components/ui/button';
import { RAGFlowPagination } from '@/components/ui/ragflow-pagination';
import { useTranslate } from '@/hooks/common-hooks';
import { pick } from 'lodash';
import { Plus } from 'lucide-react';
import { useCallback, useEffect } from 'react';
import { useSearchParams } from 'umi';
import { useFetchSearchList, useRenameSearch } from './hooks';
import { SearchCard } from './search-card';

export default function SearchList() {
  const { t } = useTranslate('search');
  const {
    data: list,
    pagination,
    searchString,
    handleInputChange,
    setPagination,
    refetch: refetchList,
  } = useFetchSearchList();

  const {
    openCreateModal,
    showSearchRenameModal,
    hideSearchRenameModal,
    searchRenameLoading,
    onSearchRenameOk,
    initialSearchName,
  } = useRenameSearch();

  const onSearchRenameConfirm = (name: string) => {
    onSearchRenameOk(name, () => {
      refetchList();
    });
  };
  const openCreateModalFun = useCallback(() => {
    showSearchRenameModal();
  }, [showSearchRenameModal]);
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
      openCreateModalFun();
      searchUrl.delete('isCreate');
      setSearchUrl(searchUrl);
    }
  }, [isCreate, openCreateModalFun, searchUrl, setSearchUrl]);

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-10 w-full px-10 pt-8">
      {(!list?.data?.search_apps?.length ||
        list?.data?.search_apps?.length <= 0) &&
      !searchString ? (
        <div className="flex w-full items-center justify-center py-20">
          <EmptyAppCard
            showIcon
            size="large"
            className="w-[480px] p-14 bg-card border-border/50 shadow-sm"
            type={EmptyCardType.Search}
            isSearch={!!searchString}
            onClick={() => openCreateModalFun()}
          />
        </div>
      ) : (
        <>
          <ListFilterBar
            icon="searches"
            title={t('searchApps')}
            showFilter={false}
            searchString={searchString}
            onSearchChange={handleInputChange}
          >
            <Button
              onClick={() => {
                openCreateModalFun();
              }}
              className="gradient-primary shadow-glow border-none"
            >
              <Plus className="mr-2 h-4 w-4" />
              {t('createSearch')}
            </Button>
          </ListFilterBar>
          {(!list?.data?.search_apps?.length ||
            list?.data?.search_apps?.length <= 0) &&
            searchString && (
              <div className="flex w-full items-center justify-center py-20">
                <EmptyAppCard
                  showIcon
                  size="large"
                  className="w-[480px] p-14 bg-card border-border/50 shadow-sm"
                  type={EmptyCardType.Search}
                  isSearch={!!searchString}
                  onClick={() => openCreateModalFun()}
                />
              </div>
            )}
          <div className="flex-1">
            <CardSineLineContainer>
              {list?.data.search_apps.map((x) => {
                return (
                  <SearchCard
                    key={x.id}
                    data={x}
                    showSearchRenameModal={() => {
                      showSearchRenameModal(x);
                    }}
                  ></SearchCard>
                );
              })}
            </CardSineLineContainer>
          </div>
          {list?.data.total && list?.data.total > 0 && (
            <div className="flex justify-end mt-8">
              <RAGFlowPagination
                {...pick(pagination, 'current', 'pageSize')}
                total={list?.data.total}
                onChange={handlePageChange}
              />
            </div>
          )}
        </>
      )}
      {openCreateModal && (
        <RenameDialog
          hideModal={hideSearchRenameModal}
          onOk={onSearchRenameConfirm}
          initialName={initialSearchName}
          loading={searchRenameLoading}
          title={initialSearchName || t('createSearch')}
        ></RenameDialog>
      )}
    </div>
  );
}
