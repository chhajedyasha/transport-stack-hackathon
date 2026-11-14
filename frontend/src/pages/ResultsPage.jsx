import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, ArrowRight, Clock, SlidersHorizontal, Table as TableIcon } from 'lucide-react';
import { planJourney } from '../api';
import TransitRow from '../components/primitives/TransitRow';
import CompareTable from '../components/primitives/CompareTable';
import LeafletRouteMap from '../components/LeafletRouteMap';
import JourneyItinerary from '../components/JourneyItinerary';
import BottomSheet from '../components/primitives/BottomSheet';
import Skeleton from '../components/primitives/Skeleton';
import { EmptyState, ErrorState } from '../components/primitives/EmptyState';
import SegmentedControl from '../components/primitives/SegmentedControl';
import WhyThisRouteModal from '../components/WhyThisRouteModal';
import { useTranslation } from '../i18n/LanguageContext';

export default function ResultsPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { t, lang } = useTranslation();
  const queryParams = new URLSearchParams(location.search);

  const originId = queryParams.get('origin_id') || '8256';
  const originName = queryParams.get('origin_name') || originId;
  const destId = queryParams.get('dest_id') || '365';
  const destName = queryParams.get('dest_name') || destId;
  const departureTime = queryParams.get('departure_time') || '18:00';
  const initialPref = queryParams.get('preference') || 'balanced';

  const [preference, setPreference] = useState(initialPref);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [planData, setPlanData] = useState(null);
  const [selectedOptionIndex, setSelectedOptionIndex] = useState(0);
  const [showCompare, setShowCompare] = useState(false);
  const [modalOption, setModalOption] = useState(null);
  const [mobileSnap, setMobileSnap] = useState('half');

  // Real page title per route
  useEffect(() => {
    document.title = `${originName} → ${destName} | CrowdWise Delhi`;
  }, [originName, destName]);

  // Handle browser back button: close modal, compare, or sheet before leaving
  useEffect(() => {
    const handlePopState = (e) => {
      if (modalOption) {
        setModalOption(null);
        e.preventDefault();
      } else if (showCompare) {
        setShowCompare(false);
        e.preventDefault();
      }
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, [modalOption, showCompare]);

  // Fetch journey plan
  const fetchPlan = () => {
    setLoading(true);
    setError(null);

    planJourney({
      originId,
      destId,
      departureTime,
      preference,
    })
      .then((res) => {
        setPlanData(res.data);
        setSelectedOptionIndex(0);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || (lang === 'hi' ? 'यात्रा की गणना करने में विफल।' : 'Failed to calculate journey options.'));
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchPlan();
  }, [originId, destId, departureTime, preference]);

  const options = planData?.options || [];
  const selectedOption = options[selectedOptionIndex] || options[0];
  const fastestOption = planData?.fastest_baseline || options[0];

  const handlePreferenceChange = (newPref) => {
    setPreference(newPref);
    const newParams = new URLSearchParams(location.search);
    newParams.set('preference', newPref);
    navigate(`/results?${newParams.toString()}`, { replace: true });
  };

  return (
    <div className="py-4 space-y-4">
      {/* Top Breadcrumb & Route Summary Bar */}
      <div className="bg-white border border-transit-border rounded-panel p-3 sm:p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Link
            to="/"
            className="p-2 rounded-[4px] border border-transit-border bg-transit-bg hover:bg-white text-navy transition-colors min-h-[40px] min-w-[40px] flex items-center justify-center"
            title={lang === 'hi' ? 'खोज बदलें' : 'Edit search'}
            aria-label="Back to planner"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div className="min-w-0">
            <div className="flex items-center gap-2 text-xs font-bold text-navy truncate">
              <span className="truncate">{originName}</span>
              <ArrowRight className="w-3.5 h-3.5 text-teal shrink-0" />
              <span className="truncate">{destName}</span>
            </div>
            <div className="flex items-center gap-2 text-[11px] text-transit-textMuted mt-0.5">
              <Clock className="w-3 h-3" />
              <span>
                {lang === 'hi' ? `प्रस्थान ~${departureTime}` : `Departs ~${departureTime}`}
              </span>
              <span>·</span>
              <span>{t('app.historicalNote')}</span>
            </div>
          </div>
        </div>

        {/* Priority Filter & Compare Button */}
        <div className="flex items-center gap-2 self-end sm:self-auto">
          <button
            type="button"
            onClick={() => setShowCompare(!showCompare)}
            className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-semibold rounded-[4px] border transition-colors min-h-[38px] ${
              showCompare
                ? 'bg-navy text-white border-navy'
                : 'bg-white text-navy border-transit-border hover:bg-transit-bg'
            }`}
          >
            <TableIcon className="w-3.5 h-3.5" />
            <span>{showCompare ? t('results.closeCompare') : t('results.compare')}</span>
          </button>
        </div>
      </div>

      {/* Side-by-Side Compare Modal/Drawer when active */}
      {showCompare && options.length > 0 && (
        <div className="animate-fade-in">
          <CompareTable
            options={options}
            selectedOptionIndex={selectedOptionIndex}
            onSelectOption={(idx) => {
              setSelectedOptionIndex(idx);
              setShowCompare(false);
            }}
          />
        </div>
      )}

      {/* Main Content: Desktop Fixed 400px Left Panel + Map / Mobile Map + BottomSheet */}
      {loading ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          <div className="lg:col-span-5 space-y-3">
            <Skeleton count={3} />
          </div>
          <div className="hidden lg:block lg:col-span-7 h-[500px] bg-transit-bg border border-transit-border rounded-panel animate-pulse" />
        </div>
      ) : error ? (
        <ErrorState
          description={error}
          onRetry={fetchPlan}
        />
      ) : options.length === 0 ? (
        <EmptyState
          title={lang === 'hi' ? 'कोई सीधी बस नहीं मिली' : 'No direct bus route found'}
          description={
            lang === 'hi'
              ? 'इन स्टॉप के बीच कोई सीधी बस नहीं मिली। 800 मीटर के दायरे में व्यापक खोज करें या नजदीकी हब चुनें।'
              : 'No direct bus route found between these stops. Try searching wider within 800 m or select a major hub.'
          }
          actionLabel={lang === 'hi' ? 'व्यापक खोज (800 मी तक)' : 'Search wider (walk up to 800 m)'}
          onAction={() => navigate('/results?origin_id=8256&dest_id=365&departure_time=18:00&preference=' + preference)}
        />
      ) : (
        <>
          {/* DESKTOP LAYOUT (>= 1024px) */}
          <div className="hidden lg:grid lg:grid-cols-12 gap-5 items-start">
            {/* Left 400px fixed width panel with options list */}
            <div className="lg:col-span-5 space-y-3 max-h-[calc(100vh-140px)] overflow-y-auto pr-1">
              <div className="flex items-center justify-between text-xs text-transit-textMuted px-1">
                <span className="font-semibold text-navy">
                  {t('results.optionsFound', { count: options.length })}
                </span>
                <span className="text-[11px] capitalize">
                  {lang === 'hi' ? 'प्राथमिकता:' : 'Ranked for:'} {preference.replace('_', ' ')}
                </span>
              </div>

              {/* Transit Rows */}
              {options.map((opt, idx) => (
                <TransitRow
                  key={opt.trip_id || idx}
                  option={opt}
                  isRecommended={idx === 0}
                  isSelected={selectedOptionIndex === idx}
                  preference={preference}
                  onSelect={() => setSelectedOptionIndex(idx)}
                  onOpenWhyModal={(item) => setModalOption(item)}
                />
              ))}
            </div>

            {/* Right Map Canvas & Detailed Stop-by-Step Itinerary below map */}
            <div className="lg:col-span-7 space-y-3">
              <div className="bg-white border border-transit-border rounded-panel px-3 py-2 flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span className="font-mono font-bold bg-navy text-white px-2 py-0.5 rounded text-[11px]">
                    {selectedOption?.route_short_name || selectedOption?.route_id || 'Route'}
                  </span>
                  <span className="font-semibold text-navy">
                    {lang === 'hi' ? 'रूट कॉरिडोर व स्टॉप ट्रैक' : 'Route Corridor & Track'}
                  </span>
                </div>
                <div className="text-[11px] text-transit-textMuted font-medium">
                  {selectedOption?.stops?.length ? `${selectedOption.stops.length} ${lang === 'hi' ? 'स्टॉप' : 'stops'} · ${selectedOption.distance_km || 13.4} km` : ''}
                </div>
              </div>
              <LeafletRouteMap
                stops={selectedOption?.stops || []}
                shapePoints={selectedOption?.shape_points || []}
                highlightOrigin={originId}
                highlightDest={destId}
                distanceKm={selectedOption?.distance_km}
                height="380px"
              />

              {/* Detailed Step-by-Step Stop Timeline and Arrival Times below the map */}
              <JourneyItinerary
                option={selectedOption}
              />
            </div>
          </div>

          {/* MOBILE LAYOUT (< 1024px) */}
          <div className="lg:hidden relative">
            {/* Map at ~35% height */}
            <div className="mb-3 space-y-1.5">
              <div className="bg-white border border-transit-border rounded-panel px-2.5 py-1.5 flex items-center justify-between text-xs">
                <div className="flex items-center gap-1.5">
                  <span className="font-mono font-bold bg-navy text-white px-1.5 py-0.5 rounded text-[10px]">
                    {selectedOption?.route_short_name || selectedOption?.route_id || 'Route'}
                  </span>
                  <span className="font-semibold text-navy text-[11px]">
                    {lang === 'hi' ? 'रूट कॉरिडोर ट्रैक' : 'Route Track'}
                  </span>
                </div>
                <div className="text-[10px] text-transit-textMuted font-medium">
                  {selectedOption?.stops?.length ? `${selectedOption.stops.length} stops · ${selectedOption.distance_km || 13.4} km` : ''}
                </div>
              </div>
              <LeafletRouteMap
                stops={selectedOption?.stops || []}
                shapePoints={selectedOption?.shape_points || []}
                highlightOrigin={originId}
                highlightDest={destId}
                distanceKm={selectedOption?.distance_km}
                height="260px"
              />
            </div>

            {/* Results in BottomSheet */}
            <BottomSheet
              snapPoint={mobileSnap}
              onSnapChange={(snap) => setMobileSnap(snap)}
            >
              <div className="p-3 space-y-3">
                <div className="flex items-center justify-between text-xs text-transit-textMuted">
                  <span className="font-bold text-navy">
                    {t('results.optionsFound', { count: options.length })}
                  </span>
                  <span className="text-[11px] text-teal font-semibold">
                    {preference.replace('_', ' ')}
                  </span>
                </div>

                <div className="space-y-2.5 pb-16">
                  {options.map((opt, idx) => (
                    <TransitRow
                      key={opt.trip_id || idx}
                      option={opt}
                      isRecommended={idx === 0}
                      isSelected={selectedOptionIndex === idx}
                      preference={preference}
                      onSelect={() => setSelectedOptionIndex(idx)}
                      onOpenWhyModal={(item) => setModalOption(item)}
                    />
                  ))}

                  {/* Selected Journey Itinerary on Mobile */}
                  <div className="pt-2">
                    <JourneyItinerary
                      option={selectedOption}
                    />
                  </div>
                </div>
              </div>
            </BottomSheet>
          </div>
        </>
      )}

      {/* Why This Route Modal */}
      {modalOption && (
        <WhyThisRouteModal
          option={modalOption}
          fastestOption={fastestOption}
          preference={preference}
          onClose={() => setModalOption(null)}
        />
      )}
    </div>
  );
}
