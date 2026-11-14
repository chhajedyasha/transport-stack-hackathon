import React from 'react';
import { ExternalLink } from 'lucide-react';
import { AppMark } from './AppLogo';
import { useTranslation } from '../i18n/LanguageContext';

export default function Footer() {
  const { lang, t } = useTranslation();

  return (
    <footer className="bg-white border-t border-transit-border mt-12 text-transit-textMuted text-xs py-6 pb-20 sm:pb-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-4">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div className="flex items-start gap-3">
            <AppMark size={24} className="mt-0.5" />
            <div className="space-y-0.5">
              <p className="font-bold text-navy">
                CrowdWise — Delhi Public Bus Journey Planner
              </p>
              <p className="text-transit-textMuted text-xs">
                {lang === 'hi'
                  ? 'ऐतिहासिक टिकट डेटा के आधार पर बस भीड़ का अनुमान। खोज और स्थान उपकरण में सुरक्षित रहते हैं।'
                  : 'Historical bus crowdedness estimation. Searches and location stay on your device.'}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3 text-transit-textMuted text-xs">
            <a
              href="https://www.openstreetmap.org/copyright"
              target="_blank"
              rel="noreferrer"
              className="hover:text-teal underline"
            >
              OpenStreetMap
            </a>
            <span>·</span>
            <a
              href="https://delhi.transportstack.in"
              target="_blank"
              rel="noreferrer"
              className="hover:text-teal underline inline-flex items-center gap-1"
            >
              Delhi GTFS <ExternalLink className="w-3 h-3" />
            </a>
            <span>·</span>
            <a
              href="https://github.com/rajnyx/transport-stack-hackathon"
              target="_blank"
              rel="noreferrer"
              className="hover:text-teal underline inline-flex items-center gap-1"
            >
              GitHub <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>

        <div className="pt-3 border-t border-transit-border flex flex-col sm:flex-row justify-between items-center text-transit-textMuted text-[11px] gap-2">
          <p>© 2026 CrowdWise. Built for Delhi commuters.</p>
          <p>
            {lang === 'hi'
              ? 'समय सारणी डेटा दिल्ली परिवहन सेवा पर आधारित है'
              : 'Timetable data based on Delhi Public Transport specifications'}
          </p>
        </div>
      </div>
    </footer>
  );
}
