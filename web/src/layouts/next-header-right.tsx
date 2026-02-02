import { RAGFlowAvatar } from '@/components/ragflow-avatar';
import { useTheme } from '@/components/theme-provider';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { LanguageList, LanguageMap, ThemeEnum } from '@/constants/common';
import { useChangeLanguage } from '@/hooks/logic-hooks';
import { useNavigatePage } from '@/hooks/logic-hooks/navigate-hooks';
import { useNavigateWithFromState } from '@/hooks/route-hook';
import { useFetchUserInfo } from '@/hooks/use-user-setting-request';
import { Routes } from '@/routes';
import { ChevronDown, CircleHelp, Globe, Moon, Sun } from 'lucide-react';
import React from 'react';
import { useTranslation } from 'react-i18next';
import { BellButton } from './bell-button';

const handleDocHelpCLick = () => {
  window.open('https://ragflow.io/docs/dev/category/guides', 'target');
};

export function NextHeaderRight() {
  const { t } = useTranslation();
  const { navigateToOldProfile } = useNavigatePage();
  const navigate = useNavigateWithFromState();

  const changeLanguage = useChangeLanguage();
  const { setTheme, theme } = useTheme();

  const {
    data: { language = 'English', avatar, nickname },
  } = useFetchUserInfo();

  const handleItemClick = (key: string) => () => {
    changeLanguage(key);
  };

  const items = LanguageList.map((x) => ({
    key: x,
    label: <span>{LanguageMap[x as keyof typeof LanguageMap]}</span>,
  }));

  const onThemeClick = React.useCallback(() => {
    setTheme(theme === ThemeEnum.Dark ? ThemeEnum.Light : ThemeEnum.Dark);
  }, [setTheme, theme]);

  const handleLogoClick = React.useCallback(() => {
    navigate(Routes.Root);
  }, [navigate]);

  return (
    <header className="flex items-center justify-end h-14 px-6 border-b border-border bg-card/50 backdrop-blur-sm">
      <div className="flex items-center gap-2">
        {/* Language selector */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="gap-2 text-muted-foreground hover:text-foreground"
            >
              <Globe size={16} />
              <span className="text-sm">
                {LanguageMap[language as keyof typeof LanguageMap] || language}
              </span>
              <ChevronDown size={14} />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            {items.map((x) => (
              <DropdownMenuItem key={x.key} onClick={handleItemClick(x.key)}>
                {x.label}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Help */}
        <Button
          variant="ghost"
          size="icon"
          onClick={handleDocHelpCLick}
          className="text-muted-foreground hover:text-foreground"
        >
          <CircleHelp size={18} />
        </Button>

        {/* Theme toggle */}
        <Button
          variant="ghost"
          size="icon"
          className="text-muted-foreground hover:text-foreground"
          onClick={onThemeClick}
        >
          {theme === ThemeEnum.Dark ? <Sun size={18} /> : <Moon size={18} />}
        </Button>

        {/* Notification */}
        <BellButton />

        {/* User avatar */}
        <div className="ml-2">
          <RAGFlowAvatar
            name={nickname}
            avatar={avatar}
            isPerson
            className="h-8 w-8 border-2 border-primary/30 cursor-pointer transition-opacity hover:opacity-80"
            onClick={navigateToOldProfile}
          />
        </div>
      </div>
    </header>
  );
}
