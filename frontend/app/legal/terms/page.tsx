import type { Metadata } from 'next';
import LegalSkeleton from '../../../components/LegalSkeleton';

export const metadata: Metadata = { title: 'Условия использования · Terms of Service' };

export default function TermsPage() {
  return (
    <LegalSkeleton
      eyebrow="условия использования · terms"
      titleRu="Условия использования"
      titleEn="Terms of Service"
    />
  );
}
