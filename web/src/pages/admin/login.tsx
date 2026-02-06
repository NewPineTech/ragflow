import { type AxiosResponseHeaders } from 'axios';
import { useEffect, useId } from 'react';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'umi';

import { useMutation } from '@tanstack/react-query';

import { zodResolver } from '@hookform/resolvers/zod';
import { Cpu } from 'lucide-react';
import { z } from 'zod';

import Spotlight from '@/components/spotlight';
import { Button } from '@/components/ui/button';
import { CardContent, CardFooter } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Authorization } from '@/constants/authorization';

import { useAuth } from '@/hooks/auth-hooks';
import { cn } from '@/lib/utils';
import { Routes } from '@/routes';
import { login } from '@/services/admin-service';
import { rsaPsw } from '@/utils';
import authorizationUtil from '@/utils/authorization-util';
import { BgSvg } from '../login-next/bg';
import FlipCard3D from '../login-next/card';
import ThemeSwitch from './components/theme-switch';

function AdminLogin() {
  const navigate = useNavigate();
  const { t } = useTranslation('translation', { keyPrefix: 'login' });
  const { isLogin } = useAuth();

  const loginMutation = useMutation({
    mutationKey: ['adminLogin'],
    mutationFn: async (params: { email: string; password: string }) => {
      const rsaPassWord = rsaPsw(params.password) as string;
      return await login({
        email: params.email,
        password: rsaPassWord,
      });
    },
    onSuccess: (request) => {
      const { data: req, headers } = request;

      if (req?.code === 0) {
        const authorization = (headers as AxiosResponseHeaders)?.get(
          Authorization,
        );
        const token = req.data.access_token;

        const userInfo = {
          avatar: req.data.avatar,
          name: req.data.nickname,
          email: req.data.email,
        };

        authorizationUtil.setItems({
          Authorization: authorization as string,
          Token: token,
          userInfo: JSON.stringify(userInfo),
        });

        navigate('/admin/services');
      }
    },
    onError: (error) => {
      console.log('Failed:', error);
    },
    retry: false,
  });

  const loading = loginMutation.isPending;

  useEffect(() => {
    if (isLogin) {
      navigate(Routes.AdminServices);
    }
  }, [isLogin, navigate]);

  const FormSchema = z.object({
    email: z
      .string()
      .email()
      .min(1, { message: t('emailPlaceholder') }),
    password: z.string().min(1, { message: t('passwordPlaceholder') }),
    remember: z.boolean().optional(),
  });

  const formId = useId();
  const form = useForm({
    defaultValues: {
      email: '',
      password: '',
      remember: false,
    },
    resolver: zodResolver(FormSchema),
  });

  return (
    <>
      <Spotlight opcity={0.4} coverage={60} color={'#00BEB4'} />
      <Spotlight
        opcity={0.3}
        coverage={12}
        X={'10%'}
        Y={'-10%'}
        color={'#00BEB4'}
      />
      <Spotlight
        opcity={0.3}
        coverage={12}
        X={'90%'}
        Y={'-10%'}
        color={'#00BEB4'}
      />

      <div className="h-[inherit] relative overflow-auto">
        <BgSvg isPaused={true} />

        <div className="absolute top-0 flex flex-col items-center mb-12 w-full text-text-primary">
          <div className="flex items-center gap-4 px-10 pt-10 w-full mb-8">
            <div className="relative flex items-center justify-center w-12 h-12 rounded-xl gradient-primary shadow-glow">
              <Cpu className="size-7 text-white" />
            </div>
            <div className="flex flex-col leading-tight">
              <span className="text-2xl font-bold tracking-tight text-foreground">
                NPT Cortex Admin
              </span>
              <span className="text-[10px] text-muted-foreground uppercase tracking-widest font-semibold opacity-70">
                Enterprise AI Core
              </span>
            </div>
          </div>
          <h1 className="mt-[4rem] text-[42px] font-bold tracking-tight text-center mb-12">
            {t('loginTitle', { keyPrefix: 'admin' })}
          </h1>
        </div>

        <div className="relative z-10 flex flex-col items-center justify-center min-h-[90vh] px-4 sm:px-6 lg:px-8">
          <FlipCard3D isLoginPage={true}>
            <div className="w-full max-w-[540px]">
              <div className="w-full bg-bg-component backdrop-blur-sm rounded-2xl shadow-xl border border-border-button">
                <CardContent className="px-10 pt-14 pb-10">
                  <Form {...form}>
                    <form
                      id={formId}
                      className="space-y-8 text-text-primary"
                      onSubmit={form.handleSubmit((data) =>
                        loginMutation.mutate(data),
                      )}
                    >
                      <FormField
                        control={form.control}
                        name="email"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel required>{t('emailLabel')}</FormLabel>

                            <FormControl>
                              <Input
                                className="h-10"
                                placeholder={t('emailPlaceholder')}
                                autoComplete="email"
                                {...field}
                              />
                            </FormControl>

                            <FormMessage />
                          </FormItem>
                        )}
                      />

                      <FormField
                        control={form.control}
                        name="password"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel required>{t('passwordLabel')}</FormLabel>

                            <FormControl>
                              <Input
                                {...field}
                                className="h-10"
                                type="password"
                                placeholder={t('passwordPlaceholder')}
                                autoComplete="password"
                              />
                            </FormControl>

                            <FormMessage />
                          </FormItem>
                        )}
                      />

                      <FormField
                        control={form.control}
                        name="remember"
                        render={({ field }) => (
                          <FormItem className="!mt-5">
                            <FormLabel
                              className={cn(
                                'transition-colors',
                                field.value
                                  ? 'text-text-primary'
                                  : 'text-text-secondary',
                              )}
                            >
                              <FormControl>
                                <Checkbox
                                  checked={field.value}
                                  onCheckedChange={field.onChange}
                                />
                              </FormControl>

                              <span className="ml-2">{t('rememberMe')}</span>
                            </FormLabel>
                          </FormItem>
                        )}
                      />
                    </form>
                  </Form>
                </CardContent>

                <CardFooter className="px-10 pt-8 pb-14">
                  <Button
                    form={formId}
                    variant="highlighted"
                    size="lg"
                    block
                    type="submit"
                    className="gradient-primary shadow-glow text-white font-bold h-12 rounded-xl border-none hover:opacity-90 w-full transition-all hover:scale-[1.02]"
                    loading={loading}
                  >
                    {t('login')}
                  </Button>
                </CardFooter>
              </div>

              <div className="mt-8 flex justify-center">
                <ThemeSwitch />
              </div>
            </div>
          </FlipCard3D>
        </div>
      </div>
    </>
  );
}

export default AdminLogin;
