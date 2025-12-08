/**
 * useVersionCheck Hook
 * Backend'den versiyon kontrolü yapar, yeni versiyon varsa kullanıcıyı bilgilendirir
 */
import { useEffect, useRef } from 'react';
import axios from 'axios';
import { APP_VERSION } from '../config/version';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';
const CHECK_INTERVAL = 5 * 60 * 1000; // 5 dakika

export const useVersionCheck = () => {
  const hasShownNotification = useRef(false);

  useEffect(() => {
    const checkVersion = async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/v1/version`);
        const serverVersion = response.data.version;

        if (serverVersion !== APP_VERSION && !hasShownNotification.current) {
          hasShownNotification.current = true;
          
          const shouldReload = window.confirm(
            `Yeni versiyon mevcut (${serverVersion}).\n` +
            `Mevcut versiyon: ${APP_VERSION}\n\n` +
            `Sayfa yenilenecek. Onaylıyor musunuz?`
          );

          if (shouldReload) {
            // Cache'i temizle ve reload
            window.location.reload();
          } else {
            // Kullanıcı iptal ettiyse 1 saat sonra tekrar sor
            setTimeout(() => {
              hasShownNotification.current = false;
            }, 60 * 60 * 1000);
          }
        }
      } catch (error) {
        console.error('Versiyon kontrolü hatası:', error);
      }
    };

    // İlk kontrol 10 saniye sonra
    const initialTimeout = setTimeout(checkVersion, 10000);

    // Periyodik kontrol
    const interval = setInterval(checkVersion, CHECK_INTERVAL);

    return () => {
      clearTimeout(initialTimeout);
      clearInterval(interval);
    };
  }, []);
};
