import type {Preview} from '@storybook/react';
import React, {ReactNode} from 'react';
import {NextIntlClientProvider} from 'next-intl';
import '../styles/tokens.css';
import '../styles/globals.css';
import enMessages from '../messages/en.json';

const withIntl = (Story: React.ComponentType) => (
  <NextIntlClientProvider locale="en" messages={enMessages}>
    <Story />
  </NextIntlClientProvider>
);

const preview: Preview = {
  decorators: [
    (Story) => withIntl(Story as unknown as React.ComponentType<{children?: ReactNode}>)
  ],
  parameters: {
    actions: {argTypesRegex: '^on[A-Z].*'},
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/
      }
    }
  }
};

export default preview;
