"use client"

import { useEffect, useState } from "react"
import { TopBar } from "@/components/layout/TopBar"
import { Card } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Select } from "@/components/ui/Select"
import { Badge } from "@/components/ui/Badge"
import { Alert } from "@/components/ui/Alert"
import { FullSpinner } from "@/components/ui/Spinner"
import { Save, Wifi } from "lucide-react"
import { getSettings, updateSettings } from "@/lib/api"
import type { Settings } from "@/lib/types"

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    getSettings().then(setSettings).finally(() => setLoading(false))
  }, [])

  const handleSave = async () => {
    if (!settings) return
    setSaving(true)
    await updateSettings(settings)
    setSaving(false)
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
  }

  if (loading || !settings) return <FullSpinner label="Loading settings..." />

  const update = (key: keyof Settings, value: string | boolean) => {
    setSettings({ ...settings, [key]: value })
  }

  return (
    <>
      <TopBar title="Settings" subtitle="Configure API connections and preferences" />
      <div className="p-6 space-y-6 max-w-3xl">
        {/* API Configuration */}
        <Card title="API Configuration">
          <div className="space-y-4">
            <div>
              <label className="block text-xs text-[var(--text-secondary)] mb-1.5">Backend URL</label>
              <input
                type="text"
                value={settings.backend_url}
                onChange={(e) => update("backend_url", e.target.value)}
                className="w-full px-3 py-2.5 rounded-lg bg-[var(--bg)] border border-[var(--border)] text-sm text-[var(--text)] focus:outline-none focus:border-[var(--primary)] font-mono"
              />
            </div>
            <div>
              <label className="block text-xs text-[var(--text-secondary)] mb-1.5">API Key (optional)</label>
              <input
                type="password"
                value={settings.api_key}
                onChange={(e) => update("api_key", e.target.value)}
                placeholder="Leave empty for no auth"
                className="w-full px-3 py-2.5 rounded-lg bg-[var(--bg)] border border-[var(--border)] text-sm text-[var(--text)] focus:outline-none focus:border-[var(--primary)] font-mono"
              />
            </div>
            <div className="flex items-center gap-2">
              <Button variant="secondary" onClick={() => {}}>
                <Wifi className="w-4 h-4" /> Test Connection
              </Button>
              <Badge variant="warning">Mock Mode — Not Connected</Badge>
            </div>
          </div>
        </Card>

        {/* Default Preferences */}
        <Card title="Default Preferences">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Select
              label="Default GPU Vendor"
              value={settings.default_vendor}
              onChange={(v) => update("default_vendor", v)}
              options={[
                { value: "any", label: "Any" },
                { value: "nvidia", label: "NVIDIA" },
                { value: "amd", label: "AMD" },
              ]}
            />
            <Select
              label="Default Precision"
              value={settings.default_precision}
              onChange={(v) => update("default_precision", v)}
              options={[
                { value: "fp32", label: "FP32" },
                { value: "fp16", label: "FP16" },
                { value: "int8", label: "INT8" },
              ]}
            />
            <Select
              label="Default Budget Tier"
              value={settings.default_budget}
              onChange={(v) => update("default_budget", v)}
              options={[
                { value: "any", label: "Any" },
                { value: "entry", label: "Entry" },
                { value: "mid", label: "Mid" },
                { value: "high", label: "High" },
                { value: "enthusiast", label: "Enthusiast" },
                { value: "datacenter", label: "Datacenter" },
              ]}
            />
            <Select
              label="Cost Unit"
              value={settings.cost_unit}
              onChange={(v) => update("cost_unit", v)}
              options={[
                { value: "USD", label: "USD ($)" },
                { value: "EUR", label: "EUR (€)" },
              ]}
            />
            <Select
              label="Runtime Unit"
              value={settings.runtime_unit}
              onChange={(v) => update("runtime_unit", v)}
              options={[
                { value: "hours", label: "Hours" },
                { value: "minutes", label: "Minutes" },
              ]}
            />
          </div>
        </Card>

        {/* Notifications */}
        <Card title="Notifications">
          <div className="space-y-3">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={settings.notify_training_complete}
                onChange={(e) => update("notify_training_complete", e.target.checked)}
                className="w-4 h-4 rounded border-[var(--border)] bg-[var(--bg)]"
              />
              <div>
                <div className="text-sm text-[var(--text)]">Training Complete</div>
                <div className="text-xs text-[var(--text-muted)]">Get notified when a training job finishes</div>
              </div>
            </label>
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={settings.notify_anomaly}
                onChange={(e) => update("notify_anomaly", e.target.checked)}
                className="w-4 h-4 rounded border-[var(--border)] bg-[var(--bg)]"
              />
              <div>
                <div className="text-sm text-[var(--text)]">Anomaly Detected</div>
                <div className="text-xs text-[var(--text-muted)]">Get notified when training anomalies are detected</div>
              </div>
            </label>
          </div>
        </Card>

        {/* Save */}
        <div className="flex items-center gap-4">
          <Button onClick={handleSave} loading={saving}>
            <Save className="w-4 h-4" /> Save Settings
          </Button>
          {saved && (
            <Alert severity="success" className="flex-1">
              Settings saved successfully.
            </Alert>
          )}
        </div>
      </div>
    </>
  )
}
