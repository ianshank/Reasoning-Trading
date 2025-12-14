import { SettingsLayout } from '@/components/settings/SettingsLayout'
import { GeneralSettings } from '@/components/settings/GeneralSettings'
import { TradingSettings } from '@/components/settings/TradingSettings'
import { APISettings } from '@/components/settings/APISettings'
import { NotificationSettings } from '@/components/settings/NotificationSettings'
import { RiskSettings } from '@/components/settings/RiskSettings'
import { MCTSSettings } from '@/components/settings/MCTSSettings'

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-foreground">Settings</h1>
        <p className="text-muted-foreground mt-1">
          Manage your application preferences and configurations
        </p>
      </div>

      {/* Settings Layout with Tabs */}
      <SettingsLayout>
        <SettingsLayout.Tab id="general" label="General">
          <GeneralSettings />
        </SettingsLayout.Tab>

        <SettingsLayout.Tab id="trading" label="Trading">
          <TradingSettings />
        </SettingsLayout.Tab>

        <SettingsLayout.Tab id="risk" label="Risk Management">
          <RiskSettings />
        </SettingsLayout.Tab>

        <SettingsLayout.Tab id="mcts" label="MCTS">
          <MCTSSettings />
        </SettingsLayout.Tab>

        <SettingsLayout.Tab id="api" label="API">
          <APISettings />
        </SettingsLayout.Tab>

        <SettingsLayout.Tab id="notifications" label="Notifications">
          <NotificationSettings />
        </SettingsLayout.Tab>
      </SettingsLayout>
    </div>
  )
}
