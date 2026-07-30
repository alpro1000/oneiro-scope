import type { Metadata } from 'next';
import LegalSkeleton from '../../../components/LegalSkeleton';

export const metadata: Metadata = { title: 'Дисклеймер · Disclaimer' };

export default function DisclaimerPage() {
  return (
    <LegalSkeleton
      eyebrow="дисклеймер · disclaimer"
      titleRu="Дисклеймер"
      titleEn="Disclaimer"
    />
  );
}
