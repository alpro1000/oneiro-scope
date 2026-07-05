import { useTranslations } from 'next-intl';
import FaceScanner from '../../../components/FaceScanner';

export default function FacePage({
  params,
}: {
  params: { locale: string };
}) {
  const t = useTranslations('FacePage');

  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-900 via-indigo-950 to-slate-900 px-4 py-10">
      <div className="mx-auto max-w-2xl">
        <h1 className="text-center text-3xl font-bold text-white">
          {t('title')}
        </h1>
        <p className="mt-2 text-center text-slate-400">{t('subtitle')}</p>
        <div className="mt-8">
          <FaceScanner locale={params.locale} />
        </div>
      </div>
    </main>
  );
}
