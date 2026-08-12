import {render, screen} from '@testing-library/react';
import FaceTransition from '@/components/FaceTransition';

/**
 * The hand-off at the bottom of a face reading is a funnel, and funnels
 * regress silently: nothing throws when a form quietly moves behind a click
 * or an email field appears "just to send the result". These pin the three
 * decisions that make it work.
 */

jest.mock('next/navigation', () => ({
  useRouter: () => ({push: jest.fn()}),
}));

describe('FaceTransition', () => {
  it('offers a comparison rather than a purchase', () => {
    render(<FaceTransition lang="en" />);
    expect(screen.getByText(/a face does not change/i)).toBeInTheDocument();
    expect(screen.getByText(/the sky changes every day/i)).toBeInTheDocument();
    // The next step is a question, not a price.
    expect(document.body.textContent).not.toMatch(/\$|€|₽|subscribe|upgrade|buy/i);
  });

  it('asks for the birth date on this screen, not behind a click', () => {
    const {container} = render(<FaceTransition lang="en" />);
    // The date blank is present in the rendered result, so the person answers
    // where they already are. Every extra page here costs about half of them.
    expect(container.querySelector('input[type="date"]')).not.toBeNull();
    expect(screen.getByRole('button', {name: /build the chart/i})).toBeInTheDocument();
  });

  it('never asks for an email', () => {
    const {container} = render(<FaceTransition lang="ru" />);
    // Email belongs at the quota boundary or a PDF, never at the moment of
    // interest — it is the single highest-friction field on the path.
    expect(container.querySelector('input[type="email"]')).toBeNull();
    expect(document.body.textContent).not.toMatch(/e-?mail|почт/i);
  });

  it('speaks the caller\'s language', () => {
    render(<FaceTransition lang="ru" />);
    expect(screen.getByText(/лицо не меняется/i)).toBeInTheDocument();
  });
});
