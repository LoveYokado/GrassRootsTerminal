# SPDX-FileCopyrightText: 2025-2026 mid.yuki(LoveYokado)
# SPDX - License - Identifier: GPL - 2.0 - or - later
/* Service Worker for GR-BBS */

self.addEventListener('install', (event) => {
    console.log('Service Worker installing.'); 
});

self.addEventListener('activate', event => {
    console.log('Service Worker activating.');
});