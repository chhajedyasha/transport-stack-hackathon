import React, { useState, useEffect } from 'react';
import { Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import DemoBanner from './components/DemoBanner';
import Footer from './components/Footer';
import PlannerPage from './pages/PlannerPage';
import ResultsPage from './pages/ResultsPage';
import RouteDetailsPage from './pages/RouteDetailsPage';
import AnalyticsPage from './pages/AnalyticsPage';
import AboutPage from './pages/AboutPage';
import { checkHealth } from './api';

export default function App() {
  const [meta, setMeta] = useState({ data_mode: 'demo' });

  useEffect(() => {
    checkHealth()
      .then((res) => {
        if (res.meta) {
          setMeta(res.meta);
        }
      })
      .catch((err) => {
        console.warn('API health check error:', err);
      });
  }, []);

  return (
    <div className="min-h-screen flex flex-col bg-brand-canvas text-brand-navy selection:bg-brand-teal selection:text-white">
      {/* Top Demo / Provenance Banner */}
      <DemoBanner meta={meta} />

      {/* Main Header / Navigation */}
      <Navbar />

      {/* Page Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8">
        <Routes>
          <Route path="/" element={<PlannerPage />} />
          <Route path="/results" element={<ResultsPage />} />
          <Route path="/route/:id" element={<RouteDetailsPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/about" element={<AboutPage />} />
        </Routes>
      </main>

      {/* Persistent Footer */}
      <Footer />
    </div>
  );
}

