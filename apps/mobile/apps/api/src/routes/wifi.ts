import type { FastifyInstance, FastifyPluginAsync } from 'fastify';
import { scanWifiNetworks } from '../services/wifi-scanner.js';

interface WifiScanQuery {
  force?: string;
  refresh?: string;
}

export const wifiRoutes: FastifyPluginAsync = async (fastify: FastifyInstance) => {
  // Handler for scanning Wi-Fi networks
  const handleScan = async (request: any) => {
    const query = (request.query || {}) as WifiScanQuery;
    const force = query.force === 'true' || query.refresh === 'true' || request.method === 'POST';
    const result = await scanWifiNetworks({ force });
    return result;
  };

  // Standard API endpoints
  fastify.get<{ Querystring: WifiScanQuery }>('/api/wifi/networks', handleScan);
  fastify.post('/api/wifi/scan', handleScan);

  // Direct alias
  fastify.get<{ Querystring: WifiScanQuery }>('/wifi/networks', handleScan);
};
