import { BulkOperateBar } from '@/components/bulk-operate-bar';
import { FileUploadDialog } from '@/components/file-upload-dialog';
import ListFilterBar from '@/components/list-filter-bar';
import { RenameDialog } from '@/components/rename-dialog';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useRowSelection } from '@/hooks/logic-hooks/use-row-selection';
import { useFetchDocumentList } from '@/hooks/use-document-request';
import { useFetchKnowledgeBaseConfiguration } from '@/hooks/use-knowledge-request';
import { Pen, Upload } from 'lucide-react';
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useManageMetadata } from '../components/metedata/hook';
import { ManageMetadataModal } from '../components/metedata/manage-modal';
import { DatasetTable } from './dataset-table';
import { useBulkOperateDataset } from './use-bulk-operate-dataset';
import { useCreateEmptyDocument } from './use-create-empty-document';
import { useSelectDatasetFilters } from './use-select-filters';
import { useHandleUploadDocument } from './use-upload-document';

export default function Dataset() {
  const { t } = useTranslation();
  const {
    documentUploadVisible,
    hideDocumentUploadModal,
    showDocumentUploadModal,
    onDocumentUploadOk,
    documentUploadLoading,
  } = useHandleUploadDocument();

  const {
    searchString,
    documents,
    pagination,
    handleInputChange,
    setPagination,
    filterValue,
    handleFilterSubmit,
    loading,
  } = useFetchDocumentList();

  const refreshCount = useMemo(() => {
    return documents.findIndex((doc) => doc.run === '1') + documents.length;
  }, [documents]);

  const { data: dataSetData } = useFetchKnowledgeBaseConfiguration({
    refreshCount,
  });
  const { filters, onOpenChange } = useSelectDatasetFilters();

  const {
    createLoading,
    onCreateOk,
    createVisible,
    hideCreateModal,
    showCreateModal,
  } = useCreateEmptyDocument();

  const {
    manageMetadataVisible,
    showManageMetadataModal,
    hideManageMetadataModal,
    tableData,
    config: metadataConfig,
  } = useManageMetadata();

  const { rowSelection, rowSelectionIsEmpty, setRowSelection, selectedCount } =
    useRowSelection();

  const { list } = useBulkOperateDataset({
    documents,
    rowSelection,
    setRowSelection,
  });
  return (
    <section className="px-10 py-6 min-w-[850px]">
      <ListFilterBar
        title="Dataset"
        icon="dataset"
        onSearchChange={handleInputChange}
        searchString={searchString}
        value={filterValue}
        onChange={handleFilterSubmit}
        onOpenChange={onOpenChange}
        filters={filters}
        leftPanel={
          <div className="items-start">
            <div className="pb-1 text-2xl font-bold tracking-tight">
              {t('knowledgeDetails.subbarFiles')}
            </div>
            <div className="text-text-secondary text-sm">
              {t('knowledgeDetails.datasetDescription')}
            </div>
          </div>
        }
        preChildren={
          <Button
            variant={'outline'}
            className="rounded-xl border-border/50 bg-background/50 hover:bg-sidebar-accent transition-all duration-300 h-10 gap-2"
            onClick={() => showManageMetadataModal()}
          >
            <Pen className="size-4 text-primary" />
            <span className="font-semibold">
              {t('knowledgeDetails.metadata.metadata')}
            </span>
          </Button>
        }
      >
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button className="gradient-primary h-10 rounded-xl px-5 font-semibold shadow-glow border-none">
              <Upload className="size-4 mr-2" />
              {t('knowledgeDetails.addFile')}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-56">
            <DropdownMenuItem onClick={showDocumentUploadModal}>
              {t('fileManager.uploadFile')}
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={showCreateModal}>
              {t('knowledgeDetails.emptyFiles')}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </ListFilterBar>
      {rowSelectionIsEmpty || (
        <BulkOperateBar list={list} count={selectedCount}></BulkOperateBar>
      )}
      <DatasetTable
        documents={documents}
        pagination={pagination}
        setPagination={setPagination}
        rowSelection={rowSelection}
        setRowSelection={setRowSelection}
        showManageMetadataModal={showManageMetadataModal}
        loading={loading}
      ></DatasetTable>
      {documentUploadVisible && (
        <FileUploadDialog
          hideModal={hideDocumentUploadModal}
          onOk={onDocumentUploadOk}
          loading={documentUploadLoading}
          showParseOnCreation
        ></FileUploadDialog>
      )}
      {createVisible && (
        <RenameDialog
          hideModal={hideCreateModal}
          onOk={onCreateOk}
          loading={createLoading}
          title={'File Name'}
        ></RenameDialog>
      )}
      {manageMetadataVisible && (
        <ManageMetadataModal
          title={
            metadataConfig.title || (
              <div className="flex flex-col gap-2">
                <div className="text-base font-normal">
                  {t('knowledgeDetails.metadata.manageMetadata')}
                </div>
                <div className="text-sm text-text-secondary">
                  {t('knowledgeDetails.metadata.manageMetadataForDataset')}
                </div>
              </div>
            )
          }
          visible={manageMetadataVisible}
          hideModal={hideManageMetadataModal}
          // selectedRowKeys={selectedRowKeys}
          tableData={tableData}
          isCanAdd={metadataConfig.isCanAdd}
          isDeleteSingleValue={metadataConfig.isDeleteSingleValue}
          type={metadataConfig.type}
          otherData={metadataConfig.record}
        />
      )}
    </section>
  );
}
