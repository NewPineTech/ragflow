import Image from '@/components/image';
import SvgIcon from '@/components/svg-icon';
import { IReferenceChunk, IReferenceObject } from '@/interfaces/database/chat';
import { getExtension } from '@/utils/document-util';
import DOMPurify from 'dompurify';
import { memo, useCallback, useEffect, useMemo, useState } from 'react';
import Markdown from 'react-markdown';
import SyntaxHighlighter from 'react-syntax-highlighter';
import rehypeKatex from 'rehype-katex';
import rehypeRaw from 'rehype-raw';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import { visitParents } from 'unist-util-visit-parents';

import { useTranslation } from 'react-i18next';

import 'katex/dist/katex.min.css'; // `rehype-katex` does not import the CSS for you

import {
  preprocessLaTeX,
  replaceTextByOldReg,
  replaceThinkToSection,
  showImage,
} from '@/utils/chat';

import { useFetchDocumentThumbnailsByIds } from '@/hooks/use-document-request';
import classNames from 'classnames';
import { omit } from 'lodash';
import { pipe } from 'lodash/fp';
import { CircleAlert } from 'lucide-react';
import { ImageCarousel } from '../markdown-content/image-carousel';
import {
  groupConsecutiveReferences,
  shouldShowCarousel,
} from '../markdown-content/reference-utils';
import { Button } from '../ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import styles from './index.less';

// Helper function to convert IReferenceObject to IReference
const convertReferenceObjectToReference = (
  referenceObject: IReferenceObject,
) => {
  const chunks = Object.values(referenceObject.chunks);
  const docAggs = Object.values(referenceObject.doc_aggs);
  return {
    chunks,
    doc_aggs: docAggs,
    total: chunks.length,
  };
};

const getChunkIndex = (match: string) => Number(match);
// TODO: The display of the table is inconsistent with the display previously placed in the MessageItem.
function MarkdownContent({
  reference,
  clickDocumentButton,
  content,
}: {
  content: string;
  loading: boolean;
  reference?: IReferenceObject;
  clickDocumentButton?: (documentId: string, chunk: IReferenceChunk) => void;
}) {
  const { t } = useTranslation();
  const { setDocumentIds, data: fileThumbnails } =
    useFetchDocumentThumbnailsByIds();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedChunkIndex, setSelectedChunkIndex] = useState<number | null>(
    null,
  );
  const contentWithCursor = useMemo(() => {
    let text = DOMPurify.sanitize(content, {
      ADD_TAGS: ['think', 'section'],
      ADD_ATTR: ['class'],
    });
    // let text = content;
    if (text === '') {
      text = t('chat.searching');
    }
    const nextText = replaceTextByOldReg(text);
    return pipe(replaceThinkToSection, preprocessLaTeX)(nextText);
  }, [content, t]);

  useEffect(() => {
    const docAggs = reference?.doc_aggs;
    setDocumentIds(Array.isArray(docAggs) ? docAggs.map((x) => x.doc_id) : []);
  }, [reference, setDocumentIds]);

  const handleDocumentButtonClick = useCallback(
    (
      documentId: string,
      chunk: IReferenceChunk,
      isPdf: boolean,
      documentUrl?: string,
    ) =>
      () => {
        if (!isPdf) {
          if (!documentUrl) {
            return;
          }
          window.open(documentUrl, '_blank');
        } else {
          clickDocumentButton?.(documentId, chunk);
        }
      },
    [clickDocumentButton],
  );

  const rehypeWrapReference = () => {
    return function wrapTextTransform(tree: any) {
      visitParents(tree, 'text', (node, ancestors) => {
        const latestAncestor = ancestors.at(-1);
        if (
          latestAncestor.tagName !== 'custom-typography' &&
          latestAncestor.tagName !== 'code'
        ) {
          node.type = 'element';
          node.tagName = 'custom-typography';
          node.properties = {};
          node.children = [{ type: 'text', value: node.value }];
        }
      });
    };
  };

  const getReferenceInfo = useCallback(
    (chunkIndex: number) => {
      const chunks = reference?.chunks ?? {};
      const chunkItem = chunks[chunkIndex];

      const documentList = Object.values(reference?.doc_aggs ?? {});
      const document = documentList.find(
        (x) => x?.doc_id === chunkItem?.document_id,
      );
      const documentId = document?.doc_id;
      const documentUrl = document?.url;
      const fileThumbnail = documentId ? fileThumbnails[documentId] : '';
      const fileExtension = documentId ? getExtension(document?.doc_name) : '';
      const imageId = chunkItem?.image_id;

      return {
        documentUrl,
        fileThumbnail,
        fileExtension,
        imageId,
        chunkItem,
        documentId,
        document,
      };
    },
    [fileThumbnails, reference],
  );

  const renderDialogContent = useCallback(
    (chunkIndex: number) => {
      const {
        documentUrl,
        fileThumbnail,
        fileExtension,
        imageId,
        chunkItem,
        documentId,
        document,
      } = getReferenceInfo(chunkIndex);

      return (
        <div key={chunkItem?.id} className="flex gap-2 max-w-md">
          {imageId && (
            <Image id={imageId} className={styles.referenceChunkImage}></Image>
          )}
          <div className={'space-y-2 min-w-0 flex-1'}>
            <div
              dangerouslySetInnerHTML={{
                __html: DOMPurify.sanitize(chunkItem?.content ?? ''),
              }}
              className={classNames(styles.chunkContentText, 'break-words')}
            ></div>
            {documentId && (
              <div className="flex gap-1">
                {fileThumbnail ? (
                  <img
                    src={fileThumbnail}
                    alt=""
                    className={styles.fileThumbnail}
                  />
                ) : (
                  <SvgIcon
                    name={`file-icon/${fileExtension}`}
                    width={24}
                  ></SvgIcon>
                )}
                <Button
                  variant="link"
                  onClick={handleDocumentButtonClick(
                    documentId,
                    chunkItem,
                    fileExtension === 'pdf',
                    documentUrl,
                  )}
                  className="text-ellipsis text-wrap"
                >
                  {document?.doc_name}
                </Button>
              </div>
            )}
          </div>
        </div>
      );
    },
    [getReferenceInfo, handleDocumentButtonClick],
  );

  const renderReference = useCallback(
    (text: string) => {
      const groups = groupConsecutiveReferences(text);
      const elements = [];
      let lastIndex = 0;

      const convertedReference = reference
        ? convertReferenceObjectToReference(reference)
        : null;

      groups.forEach((group, groupIndex) => {
        if (group[0].start > lastIndex) {
          elements.push(text.substring(lastIndex, group[0].start));
        }

        if (
          convertedReference &&
          shouldShowCarousel(group, convertedReference)
        ) {
          elements.push(
            <ImageCarousel
              key={`carousel-${groupIndex}`}
              group={group}
              reference={convertedReference}
              fileThumbnails={fileThumbnails}
              onImageClick={handleDocumentButtonClick}
            />,
          );
        } else {
          group.forEach((ref) => {
            const chunkIndex = getChunkIndex(ref.id);
            const {
              documentUrl,
              fileExtension,
              imageId,
              chunkItem,
              documentId,
            } = getReferenceInfo(chunkIndex);
            const docType = chunkItem?.doc_type;

            if (showImage(docType)) {
              elements.push(
                <section key={ref.id}>
                  <Image
                    id={imageId}
                    className={styles.referenceInnerChunkImage}
                    onClick={
                      documentId
                        ? handleDocumentButtonClick(
                            documentId,
                            chunkItem,
                            fileExtension === 'pdf',
                            documentUrl,
                          )
                        : () => {}
                    }
                  />
                  <span className="text-accent-primary"> {imageId}</span>
                </section>,
              );
            } else {
              elements.push(
                <button
                  key={ref.id}
                  type="button"
                  className="inline-block cursor-pointer"
                  onClick={() => {
                    setSelectedChunkIndex(chunkIndex);
                    setDialogOpen(true);
                  }}
                >
                  <CircleAlert className="size-4 inline-block text-blue-500 hover:text-blue-700" />
                </button>,
              );
            }
          });
        }

        lastIndex = group[group.length - 1].end;
      });

      if (lastIndex < text.length) {
        elements.push(text.substring(lastIndex));
      }

      return elements;
    },
    [
      renderDialogContent,
      getReferenceInfo,
      handleDocumentButtonClick,
      reference,
      fileThumbnails,
    ],
  );

  return (
    <>
      <Markdown
        rehypePlugins={[rehypeWrapReference, rehypeKatex, rehypeRaw]}
        remarkPlugins={[remarkGfm, remarkMath]}
        className={styles.markdownContentWrapper}
        components={
          {
            'custom-typography': ({ children }: { children: string }) =>
              renderReference(children),
            code(props: any) {
              const { children, className, ...rest } = props;
              const restProps = omit(rest, 'node');
              const match = /language-(\w+)/.exec(className || '');
              return match ? (
                <SyntaxHighlighter
                  {...restProps}
                  PreTag="div"
                  language={match[1]}
                  wrapLongLines
                >
                  {String(children).replace(/\n$/, '')}
                </SyntaxHighlighter>
              ) : (
                <code
                  {...restProps}
                  className={classNames(className, 'text-wrap')}
                >
                  {children}
                </code>
              );
            },
          } as any
        }
      >
        {contentWithCursor}
      </Markdown>
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[70vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{t('chat.references')}</DialogTitle>
          </DialogHeader>
          <div className="mt-4">
            {selectedChunkIndex !== null &&
              renderDialogContent(selectedChunkIndex)}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

export default memo(MarkdownContent);
