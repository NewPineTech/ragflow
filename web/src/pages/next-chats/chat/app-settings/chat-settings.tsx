import { Button } from '@/components/ui/button';
import { Form } from '@/components/ui/form';
import { Separator } from '@/components/ui/separator';
import { DatasetMetadata } from '@/constants/chat';
import { useFetchDialog, useSetDialog } from '@/hooks/use-chat-request';
import {
  removeUselessFieldsFromValues,
  setLLMSettingEnabledValues,
} from '@/utils/form';
import { zodResolver } from '@hookform/resolvers/zod';
import { omit } from 'lodash';
import { X } from 'lucide-react';
import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useParams } from 'umi';
import { z } from 'zod';
import ChatBasicSetting from './chat-basic-settings';
import { ChatModelSettings } from './chat-model-settings';
import { ChatPromptEngine } from './chat-prompt-engine';
import { SavingButton } from './saving-button';
import { useChatSettingSchema } from './use-chat-setting-schema';

type ChatSettingsProps = { switchSettingVisible(): void };
export function ChatSettings({ switchSettingVisible }: ChatSettingsProps) {
  const formSchema = useChatSettingSchema();
  const { data } = useFetchDialog();
  const { setDialog, loading } = useSetDialog();
  const { id } = useParams();
  const { t } = useTranslation();

  type FormSchemaType = z.infer<typeof formSchema>;

  const form = useForm<FormSchemaType>({
    resolver: zodResolver(formSchema),
    shouldUnregister: true,
    defaultValues: {
      name: '',
      icon: '',
      description: '',
      kb_ids: [],
      prompt_config: {
        quote: true,
        keyword: false,
        tts: false,
        use_kg: false,
        refine_multiturn: true,
        system: '',
        parameters: [],
        reasoning: false,
        cross_languages: [],
        toc_enhance: false,
      },
      top_n: 8,
      similarity_threshold: 0.2,
      vector_similarity_weight: 0.2,
      top_k: 1024,
      meta_data_filter: {
        method: DatasetMetadata.Disabled,
        manual: [],
      },
    },
  });

  async function onSubmit(values: FormSchemaType) {
    const nextValues: Record<string, any> = removeUselessFieldsFromValues(
      values,
      'llm_setting.',
    );

    setDialog({
      ...omit(data, 'operator_permission'),
      ...nextValues,
      dialog_id: id,
    });
  }

  function onInvalid(errors: any) {
    console.log('Form validation failed:', errors);
  }

  useEffect(() => {
    const llmSettingEnabledValues = setLLMSettingEnabledValues(
      data.llm_setting,
    );

    const nextData = {
      ...data,
      ...llmSettingEnabledValues,
    };
    form.reset(nextData as FormSchemaType);
  }, [data, form]);

  return (
    <section className="flex flex-col h-full flex-1 min-w-0 bg-transparent overflow-hidden">
      <div className="flex justify-between items-center text-lg font-bold tracking-tight p-6 pb-4">
        {t('chat.chatSetting')}
        <X
          className="size-4 cursor-pointer text-muted-foreground hover:text-foreground transition-colors"
          onClick={switchSettingVisible}
        />
      </div>
      <Form {...form}>
        <form
          onSubmit={form.handleSubmit(onSubmit, onInvalid)}
          className="flex-1 flex flex-col min-h-0 overflow-hidden"
        >
          <div className="flex-1 overflow-auto min-h-0 px-6 space-y-8 pb-8 custom-scrollbar">
            <div className="space-y-6">
              <ChatBasicSetting />
              <Separator className="opacity-40" />
              <ChatPromptEngine />
              <Separator className="opacity-40" />
              <ChatModelSettings />
            </div>
          </div>
          <div className="flex justify-end gap-3 p-6 pt-4 border-t border-border/40 bg-background/20 backdrop-blur-sm">
            <Button
              variant="outline"
              onClick={switchSettingVisible}
              className="rounded-xl px-6 h-10 font-semibold border-border/50 hover:bg-sidebar-accent transition-all duration-300"
            >
              {t('chat.cancel')}
            </Button>
            <SavingButton loading={loading}></SavingButton>
          </div>
        </form>
      </Form>
    </section>
  );
}
