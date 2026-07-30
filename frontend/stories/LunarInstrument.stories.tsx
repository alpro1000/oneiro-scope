import type {Meta, StoryObj} from '@storybook/react';
import LunarInstrument from '@/components/LunarInstrument';

const meta: Meta<typeof LunarInstrument> = {
  title: 'Calendar/LunarInstrument',
  component: LunarInstrument,
  decorators: [
    (Story) => (
      <div style={{background: 'var(--abyss)', minHeight: '100vh'}}>
        <Story />
      </div>
    )
  ]
};

export default meta;

type Story = StoryObj<typeof LunarInstrument>;

export const Default: Story = {
  args: {
    locale: 'en',
    defaultTz: 'Europe/Moscow',
    initial: {
      date: '2024-05-14',
      lunar_day: 6,
      phase: 'Waxing Crescent',
      description: 'Intuitive dreams with a focus on gentle planning.',
      recommendation: 'Write down subtle feelings, revisit your intentions, move slowly.',
      locale: 'en',
      source: 'storybook',
      timezone: 'Europe/Moscow',
      illumination: 0.42,
      phase_key: 'waxing_crescent',
      lunar_day_start_time: '08:14',
      moon_sign: 'Cancer',
      ephemeris_engine: 'SWIEPH',
      jd_ut: 2460444.5
    }
  }
};
