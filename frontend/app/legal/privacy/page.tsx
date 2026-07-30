import type { Metadata } from 'next';
import LegalSkeleton from '../../../components/LegalSkeleton';

export const metadata: Metadata = { title: 'Политика конфиденциальности · Privacy Policy' };

export default function PrivacyPage() {
  return (
    <LegalSkeleton
      eyebrow="политика конфиденциальности · privacy"
      titleRu="Политика конфиденциальности"
      titleEn="Privacy Policy"
    />
  );
}
