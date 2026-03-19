# SPDX-FileCopyrightText: 2025-2026 LoveYokado
# SPDX - License - Identifier: GPL - 2.0 - or - later

/* global PWA_URLS, textData */

if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register(PWA_URLS.serviceWorker);
    });
}