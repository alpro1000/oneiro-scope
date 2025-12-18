import '@testing-library/jest-dom';
import 'whatwg-fetch';

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    prefetch: jest.fn(),
  }),
  usePathname: () => '/en',
  useParams: () => ({locale: 'en'}),
  useSearchParams: () => new URLSearchParams(),
}));

// Mock Header component to avoid Next.js routing issues in tests
jest.mock('./components/Header', () => {
  return function MockHeader() {
    return null;
  };
});

afterEach(() => {
  jest.restoreAllMocks();
});
