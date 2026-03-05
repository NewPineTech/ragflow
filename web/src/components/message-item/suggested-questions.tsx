import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { motion } from 'framer-motion';
import { MessageCircle } from 'lucide-react';
import React from 'react';

interface SuggestedQuestionsProps {
  questions: string[];
  onQuestionClick: (question: string) => void;
  className?: string;
  disabled?: boolean;
}

export const SuggestedQuestions: React.FC<SuggestedQuestionsProps> = ({
  questions,
  onQuestionClick,
  className,
  disabled = false,
}) => {
  if (!questions || questions.length === 0) {
    return null;
  }

  return (
    <div className={cn('flex flex-col gap-2 mt-4', className)}>
      <div className="flex items-center gap-1.5 text-xs text-text-secondary">
        <MessageCircle size={14} className="opacity-70" />
        <span>Gợi ý câu hỏi</span>
      </div>
      <div className="flex flex-wrap gap-2">
        {questions.map((question, index) => (
          <motion.div
            key={index}
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: index * 0.1 }}
          >
            <Button
              variant="outline"
              size="sm"
              disabled={disabled}
              className={cn(
                'text-xs py-1 h-auto font-normal rounded-full transition-all duration-200',
                'bg-bg-card border-border-card text-text-primary',
                'hover:bg-primary/5 hover:text-primary hover:border-primary/30',
                'active:scale-95 text-left flex-wrap max-w-full',
              )}
              onClick={() => onQuestionClick(question)}
            >
              <span className="truncate whitespace-normal line-clamp-2 text-left">
                {question}
              </span>
            </Button>
          </motion.div>
        ))}
      </div>
    </div>
  );
};
