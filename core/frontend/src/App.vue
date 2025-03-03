<template>
  <v-app>
    <v-card
      flat
    >
      <v-app-bar
        app
        rounded="0"
        :color="app_bar_color"
        :height="toolbar_height"
      >
        <v-app-bar-nav-icon
          id="hamburguer-menu-button"
          :style="{ visibility: drawer ? 'hidden' : 'visible' }"
          color="white"
          @click="drawer = true"
        />

        <v-spacer />
        <span class="d-flex flex-column align-center">
          <backend-status-checker @statusChange="changeBackendStatus" />
        </span>
        <v-spacer />
        <beacon-tray-menu />
        <health-tray-menu />
        <theme-tray-menu />
        <vehicle-reboot-required-tray-menu />
        <pirate-mode-tray-menu />
        <wifi-tray-menu />
        <ethernet-tray-menu />
        <notification-tray-button />
      </v-app-bar>
    </v-card>

    <v-navigation-drawer
      v-model="drawer"
      app
      fixed
      @input="drawerEvent"
    >
      <v-container
        elevation="0"
        class="d-flex justify-center align-center"
      >
        <v-img
          alt="Blue Robotics Logo"
          class="shrink mr-2"
          contain
          :src="blueos_logo"
          width="70%"
        />
      </v-container>
      <v-divider />
      <v-container
        elevation="0"
        class="d-flex justify-center align-center pa-0"
      >
        <vehicle-banner />
      </v-container>

      <v-container
        class="pa-1"
      >
        <v-divider />
        <v-list
          v-for="(menu, i) in computed_menu"
          :key="i"
          class="pa-0"
          nav
          dense
        >
          <v-list-item-group color="primary">
            <v-list-group
              v-if="menu.submenus"
              :id="'button-to-' + menu.title.toLowerCase()"
              :prepend-icon="menu.icon"
              :to="menu.route"
              no-action
            >
              <template #activator>
                <v-list-item-title>
                  {{ menu.title }}
                  <v-chip
                    v-if="menu.beta"
                    class="ma-2 pl-2 pr-2"
                    color="red"
                    pill
                    x-small
                    text-color="white"
                  >
                    Alpha
                  </v-chip>
                </v-list-item-title>
              </template>

              <template
                v-for="(submenu, j) in menu.submenus"
              >
                <v-list-item
                  v-if="!submenu.advanced || (submenu.advanced && settings.is_pirate_mode)"
                  :key="j"
                  :target="submenu?.new_page ? '_blank' : '_self'"
                  :to="submenu.route"
                  :href="menu.extension ? submenu.route : undefined"
                >
                  <v-list-item-icon style="min-width:28px;">
                    <v-icon
                      v-if="!submenu.icon.startsWith('http')"
                      class="mr-0"
                      v-text="submenu.icon"
                    />
                    <v-img
                      v-else
                      class="shrink mr-0"
                      contain
                      :src="submenu.icon"
                      width="24"
                    />
                    <v-theme-provider
                      v-if="submenu.advanced && settings.is_pirate_mode"
                      dark
                    >
                      <div
                        v-tooltip="'This is an advanced feature'"
                        class="pirate-marker ma-0"
                      >
                        <v-avatar
                          class="ma-0"
                          color="error"
                          size="15"
                        >
                          <v-icon
                            size="15"
                            v-text="'mdi-skull-crossbones'"
                          />
                        </v-avatar>
                      </div>
                    </v-theme-provider>
                  </v-list-item-icon>
                  <v-list-item-title
                    v-text="submenu.title"
                  />
                </v-list-item>
              </template>
            </v-list-group>

            <v-list-item
              v-else
              :to="menu.route"
            >
              <v-list-item-icon>
                <v-icon v-text="menu.icon" />
              </v-list-item-icon>

              <v-list-item-title v-text="menu.title" />
            </v-list-item>
          </v-list-item-group>
        </v-list>
        <v-divider />
        <v-container class="d-flex justify-center">
          <power-menu />
          <settings-menu />
          <report-menu />
        </v-container>
        <span
          class="build_info"
        >
          BlueOS Version:
          <a
            target="_blank"
            rel="noopener noreferrer"
            :href="git_info_url"
          >
            {{ git_info }}
          </a>
        </span>
        <span
          id="current-version"
          class="build_info"
        >Build: {{ build_date }}</span>
        <span
          class="build_info"
        >
          By
          <a
            target="_blank"
            rel="noopener noreferrer"
            href="https://bluerobotics.com"
            style="text-decoration:none;"
          >
            Blue Robotics
          </a>
        </span>
      </v-container>
    </v-navigation-drawer>

    <v-main>
      <router-view />
      <div id="tour-center-hook" />
    </v-main>
    <services-scanner />
    <ethernet-updater />
    <wifi-updater />
    <mavlink-updater />
    <new-version-notificator />
    <Wizard />
    <alerter />
    <v-tour
      name="welcomeTour"
      :steps="steps.filter((step) => step?.filter_wifi_connected !== wifi_connected)"
      :callbacks="tourCallbacks"
    />
  </v-app>
</template>

<script lang="ts">
import Vue from 'vue'

import blueos_blue from '@/assets/img/blueos-logo-blue.svg'
import blueos_white from '@/assets/img/blueos-logo-white.svg'
import Wizard from '@/components/wizard/Wizard.vue'
import settings from '@/libs/settings'
import services_scanner from '@/store/servicesScanner'
import wifi from '@/store/wifi'
import { Service } from '@/types/helper'
import { convertGitDescribeToUrl } from '@/utils/helper_functions'
import updateTime from '@/utils/update_time'

import Alerter from './components/app/Alerter.vue'
import BackendStatusChecker from './components/app/BackendStatusChecker.vue'
import NewVersionNotificator from './components/app/NewVersionNotificator.vue'
import PiradeModeTrayMenu from './components/app/PirateModeTrayMenu.vue'
import PowerMenu from './components/app/PowerMenu.vue'
import ReportMenu from './components/app/ReportMenu.vue'
import SettingsMenu from './components/app/SettingsMenu.vue'
import ThemeTrayMenu from './components/app/ThemeTrayMenu.vue'
import VehicleBanner from './components/app/VehicleBanner.vue'
import VehicleRebootRequiredTrayMenu from './components/app/VehicleRebootRequiredTrayMenu.vue'
import BeaconTrayMenu from './components/beacon/BeaconTrayMenu.vue'
import EthernetTrayMenu from './components/ethernet/EthernetTrayMenu.vue'
import EthernetUpdater from './components/ethernet/EthernetUpdater.vue'
import HealthTrayMenu from './components/health/HealthTrayMenu.vue'
import MavlinkUpdater from './components/mavlink/MavlinkUpdater.vue'
import NotificationTrayButton from './components/notifications/TrayButton.vue'
import ServicesScanner from './components/scanner/servicesScanner.vue'
import WifiTrayMenu from './components/wifi/WifiTrayMenu.vue'
import WifiUpdater from './components/wifi/WifiUpdater.vue'
import menus from './menus'

/**
 * Menu interface to populate UI
 */
interface Menu {
  title: string,
  icon: string,
  text?: string, // Option description

  advanced?: boolean, // The option will only be enable in pirate mode
  beta?: boolean, // Used on menus that are in development
  extension?: boolean, // True if is an extension
  new_page?: string, // The address will open in a new page
  route?: string, // The option routes to a different address
  submenus?: Menu[], // Menus that the main option provide
}

export default Vue.extend({
  name: 'App',

  components: {
    'beacon-tray-menu': BeaconTrayMenu,
    'notification-tray-button': NotificationTrayButton,
    'pirate-mode-tray-menu': PiradeModeTrayMenu,
    'theme-tray-menu': ThemeTrayMenu,
    'services-scanner': ServicesScanner,
    'wifi-tray-menu': WifiTrayMenu,
    'wifi-updater': WifiUpdater,
    'ethernet-tray-menu': EthernetTrayMenu,
    'ethernet-updater': EthernetUpdater,
    'health-tray-menu': HealthTrayMenu,
    'mavlink-updater': MavlinkUpdater,
    'power-menu': PowerMenu,
    'settings-menu': SettingsMenu,
    'report-menu': ReportMenu,
    'backend-status-checker': BackendStatusChecker,
    Alerter,
    'vehicle-banner': VehicleBanner,
    'new-version-notificator': NewVersionNotificator,
    VehicleRebootRequiredTrayMenu,
    Wizard,
  },

  data: () => ({
    settings,
    drawer: undefined as boolean|undefined,
    drawer_running_tour: false,
    backend_offline: false,
    menus,
    tourCallbacks: {}, // we are setting this up in mounted otherwise "this" can be undefined
  }),
  computed: {
    wifi_connected(): boolean {
      return wifi.current_network != null
    },
    toolbar_height(): number {
      return settings.is_pirate_mode && this.backend_offline ? 66 : 56
    },
    computed_menu(): Menu[] {
      const submenus = services_scanner.services
        .filter((service: Service) : boolean => service.metadata !== null)
        .map((service: Service) => {
          const address = this.createExtensionAddress(service)
          return {
            title: service.metadata?.name ?? 'Service name',
            icon: service.metadata?.icon?.startsWith('/')
              ? `${address}${service.metadata.icon}`
              : service.metadata?.icon ?? 'mdi-puzzle',
            route: service.metadata?.route ?? address,
            new_page: service.metadata?.new_page ?? undefined,
            advanced: false,
            text: service.metadata?.description ?? 'Service text',
          }
        })

      const extensions: Menu = {
        title: 'Extensions',
        icon: 'mdi-puzzle',
        extension: true,
        beta: true,
        submenus: [
          {
            title: 'Extensions Manager',
            icon: 'mdi-puzzle',
            route: '/tools/extensions-manager',
            advanced: false,
            text: 'Manage BlueOS extensions',
          },
          ...submenus,
        ] as Menu[],
      }

      return [...this.menus, extensions]
    },
    steps() {
      return [
        {
          target: '#tour-center-hook',
          header: {
            title: 'Welcome to BlueOS!',
          },
          content: `We are happy to have you navigating with us! BlueOS provides the
          necessary tools to configure your vehicle, check the system status and more.
          Follow this quick tour to get familiar with your brand new onboard system.`,
          params: {
            enableScrolling: false,
          },
        },
        {
          target: '#tour-center-hook',
          content: 'Connect BlueOS to the internet to enable online functionalities.',
          filter_wifi_connected: true,
          params: {
            enableScrolling: false,
          },
        },
        {
          target: '#wifi-tray-menu-button',
          content: 'You can do it by connecting to a wifi network...',
          filter_wifi_connected: true,
          params: {
            enableScrolling: false,
          },
        },
        {
          target: '#ethernet-tray-menu-button',
          content: '...or by connecting to a cable internet (usually from/to a router).',
          filter_wifi_connected: true,
          params: {
            enableScrolling: false,
          },
        },
        {
          target: '#button-to-vehicle',
          content: 'This is the main BlueOS menu. Here you can access all the running services and system utilities.',
          params: {
            enableScrolling: false,
            placement: 'right',
          },
          before: () => {
            // It's necessary to control the drawer tour event otherwise the internal state control will close it
            this.drawer_running_tour = true
            // We will open the drawer for the message
            this.drawer = true
          },
        },
        {
          target: '#button-to-vehicle',
          content: `Under the Vehicle menu, you can check the status of your autopilot, download logs from it,
          set up video streams and even update its firmware!`,
          params: {
            enableScrolling: false,
          },
        },
        {
          target: '#button-to-tools',
          content: `Here you can find all kinds of tools to improve your BlueOS experience.
          There are system-diagnosis tools, like network-speed tester and others, all under the Tools menu.`,
          params: {
            enableScrolling: false,
          },
        },
        {
          target: '#power-menu-button',
          content: 'Here you can safely shut down or restart the running computer.',
          params: {
            enableScrolling: false,
          },
        },
        {
          target: '#settings-menu-button',
          content: 'With the settings button, you can customize your BlueOS experience.',
          params: {
            enableScrolling: false,
          },
        },
        {
          target: '#feature-request-button',
          content: `Here you can get in touch with us, request new features, report bugs, interact with our
          community, and more!`,
          params: {
            enableScrolling: false,
          },
        },
        {
          target: '#current-version',
          content: `You can check the version of BlueOS installed here. This version number is particularly important
          when looking for help.`,
          params: {
            enableScrolling: false,
          },
        },
        {
          target: '#notifications-tray-menu-button',
          content: 'Last but not least, you can find any event related to your system under the notifications menu.',
          before: () => {
            // The close vent will happen after the next tick of the state control
            this.drawer_running_tour = false
          },
          params: {
            enableScrolling: false,
          },
        },
        {
          target: '#tour-center-hook',
          content: `That's it! Now we want you to enjoy your experience with BlueOS! Also, don't forget to get in touch
          if you need anything else to improve your journey! Happy exploring!`,
          params: {
            enableScrolling: false,
          },
        },
      ]
    },
    git_info(): string {
      return process.env.VUE_APP_GIT_DESCRIBE
    },
    git_info_url(): string {
      return convertGitDescribeToUrl(process.env.VUE_APP_GIT_DESCRIBE)
    },
    build_date(): string {
      return process.env.VUE_APP_BUILD_DATE
    },
    app_bar_color(): string {
      return this.backend_offline ? 'grey darken-1' : 'primary'
    },
    blueos_logo(): string {
      return settings.is_dark_theme ? blueos_white : blueos_blue
    },
  },

  watch: {
    $route() {
      // In an update process the page may not be the 'Main' page, check tour when page changes
      this.checkTour()
      // Env may not exist when running it with `yarn serve`
      const project_name = process.env.PROJECT_NAME ?? 'BlueOS'
      if (this.$route.name === this.$router.options.routes!.first()!.name) {
        document.title = project_name
        return
      }

      document.title = `${this.$route.name} - ${project_name}`
    },
  },

  mounted() {
    this.checkAddress()
    this.setupCallbacks()
    this.checkTour()
    updateTime()
  },

  methods: {
    checkAddress(): void {
      if (window.location.host.includes('companion.local')) {
        window.location.replace('http://blueos.local')
      }
    },
    createExtensionAddress(service: Service): string {
      if (service?.metadata?.new_page !== true) {
        return `/extensions/${service.port}`
      }

      // The `//` force href to be used as absolute path and not as relative
      return `//${window.location.hostname}:${service.port}`
    },
    setupCallbacks(): void {
      this.tourCallbacks = {
        onSkip: this.skipTour,
        onStop: this.skipTour,
      }
    },
    skipTour(): void {
      this.drawer_running_tour = false
    },
    checkTour(): void {
      // Check the current page and tour version to be sure that we are in the correct place before starting
      if (this.$route.name === this.$router.options.routes!.first()!.name) {
        settings.run_tour_version(2)
          .then(() => this.$tours.welcomeTour.start())
          .catch((message) => console.log(message))
      }
    },
    drawerEvent(): void {
      // If we are inside the tour, let the drawer open, the function will be called by the drawer state control
      if (this.drawer_running_tour) {
        this.$nextTick(() => { this.drawer = true })
      }
    },
    changeBackendStatus(backend_offline: boolean): void {
      this.backend_offline = backend_offline
    },
  },
})
</script>

<style scoped>
html {
  overflow-y: auto
}

.active_menu {
  color: blue;
}

span.build_info {
  font-size: 70%;
  margin-left: 30px;
  display: block;
}

#tour-center-hook {
  position: absolute;
  top: 20%;
  left: 50%;
}

div.pirate-marker {
  position: relative;
  top: -10px;
  right: 7px;
  width: 15px;
  height: 15px;
  opacity: 0.7;
}

div.pirate-marker.v-icon {
    font-size: 10px;
}

/* Align home side menu item */
.v-list--nav .v-list-item {
  padding: 0 8px;
}

.v-list-item {
  padding: 0 4px;
}

.v-application--is-ltr .v-list--dense.v-list--nav .v-list-group--no-action > .v-list-group__items > .v-list-item {
  padding-left: 32px;
}

.v-navigation-drawer__content::-webkit-scrollbar {
  width: 8px;
}

.v-navigation-drawer__content::-webkit-scrollbar-track {
  box-shadow: inset 0 0 1px grey;
}

.v-navigation-drawer__content::-webkit-scrollbar-thumb {
  background: var(--v-primary-darken3);
  transition: visibility 2s;
}

.v-navigation-drawer__content::-webkit-scrollbar-thumb:hover {
  background: var(--v-primary-base);
}
</style>

<style>
/* Global style */
/* mdi-loading icon is being used ? Of course you want to rotate it! */
.mdi-loading {
  animation: rotate 2s linear infinite;
}

@keyframes rotate {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

html {
  overflow: auto
}
</style>
