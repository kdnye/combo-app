import { Briefcase, FileSpreadsheet } from 'lucide-react';
import { ToolCard, type ToolCardProps } from '@/components/ToolCard';
import { appConfig } from '@/config';

const pageCopy = {
  quote: 'Create and manage customer freight quotes across modes.',
  expenses: 'Submit and track business expenses for approval.'
};

/**
 * Provide metadata for the launcher cards surfaced on the home page.
 *
 * @returns Promise that resolves to the static set of quote and expense tools.
 */
const getToolCards = async (): Promise<ToolCardProps[]> => {
  const cards: ToolCardProps[] = [
    {
      title: 'FSI Quote Tool',
      description: pageCopy.quote,
      href: appConfig.quoteToolUrl,
      icon: Briefcase
    },
    {
      title: 'FSI Expense Reports',
      description: pageCopy.expenses,
      href: appConfig.expenseToolUrl,
      icon: FileSpreadsheet
    }
  ];

  return cards;
};

const HomePage = async () => {
  const cards = await getToolCards();

  return (
    <section aria-labelledby="dashboard-heading" className="space-y-8">
      <div className="flex flex-col gap-2">
        <h2 className="text-xl font-semibold text-muted" id="dashboard-heading">
          Quick launch
        </h2>
        <p className="text-sm text-muted">
          Access our freight quoting, expense tracking, and operations tools from a single hub.
        </p>
      </div>
      <div className="card-grid">
        {cards.map((card) => (
          <ToolCard key={card.title} {...card} />
        ))}
      </div>
    </section>
  );
};

export default HomePage;
