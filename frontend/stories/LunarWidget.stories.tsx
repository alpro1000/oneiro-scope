import type {Meta, StoryObj} from '@storybook/react';
import {NextIntlClientProvider} from 'next-intl';
import LunarWidget from '@/components/LunarWidget';
import enMessages from '@/messages/en.json';

const meta: Meta<typeof LunarWidget> = {
  title: 'Calendar/LunarWidget',
  component: LunarWidget,
  decorators: [
    (Story) => (
      <NextIntlClientProvider locale="en" messages={enMessages}>
        <div style={{background: 'var(--bg)', minHeight: '100vh', padding: '2rem'}}>
          <Story />
        </div>
      </NextIntlClientProvider>
    )
  ]
};

export default meta;

type Story = StoryObj<typeof LunarWidget>;

export const Default: Story = {
  args: {
    locale: 'en',
    initialData: {
      date: '2024-05-14',
      lunar_day: 6,
      phase: 'Waxing Crescent',
      description: 'Intuitive dreams with a focus on gentle planning.',
      recommendation: 'Write down subtle feelings, revisit your intentions, move slowly.',
      locale: 'en',
      source: 'storybook',
      timezone: 'Europe/Moscow'
    }
  }
};
