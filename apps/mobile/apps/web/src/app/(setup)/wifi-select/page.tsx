'use client';

import {
  Button,
  Card,
  EmptyState,
  ListRow,
  Screen,
  ScreenActions,
  ScreenHeader,
  cn,
} from '@adam/ui';
import type { WifiNetwork } from '@adam/types';
import { useQuery } from '@tanstack/react-query';
import { Check, Info, Lock, RotateCw, Wifi, WifiHigh, WifiLow, WifiOff, WifiZero } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { queryKeys, scanNetworks } from '@/lib/mock/api';
import { useSetupStore } from '@/stores/setup-store';

/**
 * Maps signal bars (0–4) to appropriate Lucide Wi-Fi icon.
 */
function getWifiIcon(signalBars: number, unsupported?: boolean) {
  if (unsupported) {
    return <Wifi className="h-5 w-5 opacity-40 text-fg-muted" strokeWidth={1.5} />;
  }
  switch (signalBars) {
    case 4:
      return <Wifi className="h-5 w-5 text-fg" strokeWidth={1.5} />;
    case 3:
      return <WifiHigh className="h-5 w-5 text-fg" strokeWidth={1.5} />;
    case 2:
      return <WifiLow className="h-5 w-5 text-fg" strokeWidth={1.5} />;
    case 1:
      return <WifiZero className="h-5 w-5 text-fg-muted" strokeWidth={1.5} />;
    default:
      return <WifiZero className="h-5 w-5 opacity-40 text-fg-muted" strokeWidth={1.5} />;
  }
}

/**
 * Formats row subtitle showing frequency band, security standard, and signal strength.
 */
function formatSubtitle(network: WifiNetwork): string {
  if (network.unsupported) {
    return '5 GHz only · ADAM requires 2.4 GHz';
  }

  const bandText =
    network.band === 'dual'
      ? 'Dual-band (2.4 & 5 GHz)'
      : network.band === '5GHz'
        ? '5 GHz only'
        : '2.4 GHz';

  const secText = network.security === 'open' ? 'Open' : network.security.toUpperCase();
  const signalText = network.signalPercent ? ` · ${network.signalPercent}%` : '';

  return `${bandText} · ${secText}${signalText}`;
}

/**
 * `connecting_to_wi_fi` — the network list ("Get him online.").
 *
 * Displays live scanned networks with signal strength, frequency band,
 * and security standard. Handles 5GHz-only exclusion gracefully.
 */
export default function WifiSelectPage() {
  const router = useRouter();
  const selectSsid = useSetupStore((state) => state.selectSsid);
  const complete = useSetupStore((state) => state.complete);
  const [selected, setSelected] = useState<string | null>(null);

  const {
    data: networks = [],
    isPending,
    isFetching,
    refetch,
  } = useQuery({
    queryKey: queryKeys.networks,
    queryFn: () => scanNetworks(true),
  });

  function submit() {
    if (!selected) return;
    const network = networks.find((item) => item.ssid === selected);
    selectSsid(selected);
    complete('wifi-select');
    // An open network has no password step.
    router.push(network?.security === 'open' ? '/connecting' : '/wifi-password');
  }

  return (
    <Screen className="pt-0 flex-1 min-h-0 flex flex-col justify-between" texture={false}>
      <div className="shrink-0 pt-1 pb-2 flex items-start justify-between">
        <ScreenHeader
          size="md"
          title="Get him online."
          subtitle="Select a network to connect ADAM to your local environment."
        />
        <button
          type="button"
          onClick={() => refetch()}
          disabled={isFetching}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-fg-muted transition-colors hover:bg-surface-pressed hover:text-fg disabled:opacity-40"
          aria-label="Scan for Wi-Fi networks"
          title="Rescan Wi-Fi networks"
        >
          <RotateCw className={cn('h-5 w-5', isFetching && 'animate-spin')} strokeWidth={1.5} />
        </button>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto py-2 flex flex-col gap-stack-md no-scrollbar">
        <div className="flex flex-col gap-2.5">
          {isPending
            ? Array.from({ length: 4 }, (_, index) => (
                <Card key={index} padding="none">
                  <div className="flex items-center gap-gutter px-stack-md py-gutter">
                    <span className="h-10 w-10 animate-breathe rounded-full bg-surface-pressed" />
                    <span className="h-4 w-32 animate-breathe rounded-full bg-surface-pressed" />
                  </div>
                </Card>
              ))
            : networks.length === 0
              ? (
                <EmptyState
                  icon={WifiOff}
                  title="No networks found"
                  description="Ensure your Wi-Fi adapter is turned on and try scanning again."
                  action={
                    <Button variant="outline" size="sm" onClick={() => refetch()}>
                      Scan again
                    </Button>
                  }
                />
              )
              : networks.map((network) => {
                  const isSelected = selected === network.ssid;
                  return (
                    <Card
                      key={network.ssid}
                      padding="none"
                      className={cn(
                        'transition-colors duration-fast',
                        isSelected ? 'border-fg bg-surface-raised' : 'border-border/60 bg-surface-raised/90',
                      )}
                    >
                      <ListRow
                        disabled={network.unsupported}
                        onClick={network.unsupported ? undefined : () => setSelected(network.ssid)}
                        icon={getWifiIcon(network.signalBars, network.unsupported)}
                        title={network.ssid}
                        subtitle={formatSubtitle(network)}
                        trailing={
                          <span className="flex items-center gap-stack-sm text-fg-subtle">
                            {network.band === 'dual' ? (
                              <span className="rounded bg-surface-pressed px-1.5 py-0.5 text-[11px] font-medium text-fg-muted">
                                2.4 / 5G
                              </span>
                            ) : null}
                            {network.security === 'open' ? null : (
                              <Lock className="h-4 w-4" strokeWidth={1.5} aria-label="Secured" />
                            )}
                            {isSelected ? (
                              <Check
                                className="h-5 w-5 text-fg"
                                strokeWidth={2}
                                aria-label="Selected"
                              />
                            ) : null}
                          </span>
                        }
                      />
                    </Card>
                  );
                })}
        </div>

        <p className="flex items-center gap-stack-sm text-label-sm text-fg-muted pb-2">
          <Info className="h-4 w-4 shrink-0" strokeWidth={1.5} aria-hidden />
          ADAM only supports 2.4GHz networks.
        </p>
      </div>

      <ScreenActions className="mt-auto pb-safe shrink-0 pt-2">
        <Button block variant="primary" size="lg" disabled={!selected} onClick={submit}>
          Continue
        </Button>
      </ScreenActions>
    </Screen>
  );
}
