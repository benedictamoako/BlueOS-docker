<template>
  <v-card
    elevation="0"
    class="mx-auto my-6"
  >
    <v-data-table
      :headers="[
        { text: 'Name', value: 'name' },
        { text: 'Description', value: 'description' },
        { text: 'Value', value: 'value', width: '150px' },
      ]"
      :loading="!finished_loading"
      :items="search && search != '' ? fuse.search(search) : params_no_input"
      item-key="item.name"
      class="elevation-1"
      :search="search"
      :sort-by="'name'"
      disable-sort
      :custom-filter="() => true"
      :item-class="(value) => value.item?.readonly ? undefined : 'hand-cursor'"
      @click:row="(value) => editParam(value.item)"
    >
      <v-progress-linear
        slot="progress"
        color="blue"
        height="20"
        :value="params_percentage"
      >
        <template #default>
          <strong
            v-if="!finished_loading && params_percentage > 99.9"
          >
            Waiting for metadata.. </strong>
          <strong
            v-if="params_percentage == 0"
            class="ml-5"
          > Waiting for parameters.. </strong>
          <strong
            v-if="params_percentage > 0 && params_percentage < 100"
            class="ml-5"
          >
            {{ params_percentage.toFixed(1) }}% ({{ loaded_parameters }} / {{ total_parameters }})
          </strong>
        </template>
      </v-progress-linear>
      <template #top>
        <v-text-field
          v-model="search"
          label="Search"
          class="mx-4"
          clearable
          prepend-inner-icon="mdi-magnify"
        />
      </template>
      <!-- suprresing no-vue-html -->
      <!-- eslint-disable -->
      <template #item.name="{ item }">
        <div v-html="printMark(item, 'name')" />
      </template>
      <template #item.description="{ item }">
        <div v-html="printMark(item, 'description')" />
      </template>
       <!-- eslint-enable -->
      <template #item.value="{ item }">
        {{ printParam(item.item) }} {{ item.item.units ? `[${item.item.units}]` : '' }}
      </template>
      <template #footer.prepend>
        <v-btn
          v-tooltip="'Save all parameters to file'"
          :disabled="!finished_loading"
          color="primary"
          class="mr-5"
          @click="saveParametersToFile()"
        >
          <v-icon class="mr-2">
            mdi-tray-arrow-down
          </v-icon>
          <div>Save</div>
        </v-btn>
        <v-btn
          v-tooltip="'Load parameters from file'"
          :disabled="!finished_loading"
          class="mr-5"
          color="primary"
          @click="load_param_dialog = true"
        >
          <v-icon class="mr-2">
            mdi-tray-arrow-up
          </v-icon>
          <div>Load</div>
        </v-btn>
      </template>
    </v-data-table>
    <parameter-editor-dialog
      v-model="edit_dialog"
      :param="edited_param"
    />
    <v-dialog
      v-model="load_param_dialog"
      max-width="500px"
    >
      <v-card>
        <v-card-title>
          <span class="text-h5">Load parameter file</span>
        </v-card-title>

        <v-card-text>
          <v-container>
            <v-row>
              <v-file-input
                accept=".txt"
                class="mr-2"
                show-size
                label="Parameter file"
                @change="setParameterFile"
              />
            </v-row>
            <!--v-row>
              <v-col cols="6" sm="6" md="6">
                <v-form ref="form">
                  <v-checkbox v-if="show_advanced_checkbox" v-model="forcing_input" dense :label="'Force'" />
                  <v-checkbox v-if="show_custom_checkbox" v-model="custom_input" dense :label="'Custom'" />
                </v-form>
              </v-col>
            </v-row-->
          </v-container>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn
            color="primary"
            @click="load_param_dialog = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            @click="applyParameterFile"
          >
            Save and Reboot
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script lang="ts">
import { format } from 'date-fns'
import { saveAs } from 'file-saver'
import Fuse from 'fuse.js'
import Vue from 'vue'

import mavlink2rest from '@/libs/MAVLink2Rest'
import autopilot_data from '@/store/autopilot'
import autopilot from '@/store/autopilot_manager'
import Parameter, { ParamType, printParam } from '@/types/autopilot/parameter'

import ParameterEditorDialog from './ParameterEditorDialog.vue'

export default Vue.extend({
  name: 'ParameterEditor',
  components: {
    ParameterEditorDialog,
  },
  data() {
    return {
      search: '',
      edited_param: undefined as (undefined | Parameter),
      edit_dialog: false,
      load_param_dialog: false,
      loaded_parameter: [] as {name: string, value: number, type: undefined | ParamType}[],
    }
  },
  computed: {
    fuse() {
      return new Fuse(autopilot_data.parameters, {
        keys: ['name', 'description'],
        includeScore: true,
        includeMatches: true,
        shouldSort: true,
        threshold: 0.3,
        minMatchCharLength: 2,
      })
    },
    params_no_input() {
      return autopilot_data.parameters
        .sort((a, b) => {
          if (a.name > b.name) {
            return 1
          }
          if (b.name > a.name) {
            return -1
          }
          return 0
        })
        .map((param) => ({
          item: param,
        }))
    },
    params_percentage() {
      return 100 * (autopilot_data.parameters.length / autopilot_data.parameters_total)
    },
    loaded_parameters() {
      return autopilot_data.parameters.length
    },
    total_parameters() {
      return autopilot_data.parameters_total
    },
    finished_loading() {
      return autopilot_data.finished_loading
    },
  },
  methods: {
    editParam(param: Parameter) {
      if (param.readonly) {
        return
      }
      this.edited_param = param
      this.edit_dialog = true
    },
    printMark(item: Fuse.FuseResult<Record<string, string>>, key: string): string {
      const name = item.item[key]
      const indices_array = item?.matches?.find((i: Fuse.FuseResultMatch) => i.key === key)?.indices ?? []

      let indices = indices_array?.[0]
      for (const index of indices_array) {
        if (indices[1] - indices[0] < index[1] - index[0]) {
          indices = index
        }
      }

      const matche = indices ? name.substring(indices[0], indices[1] + 1) : ''
      return indices ? name.replace(matche, `<mark>${matche}</mark>`) : name
    },
    printParam,
    saveParametersToFile() {
      let parameter_name_max_size = 0

      // Sort parameters alphabetically
      // We take advantage of sort to also calculate the parameter name maximum size
      const parameters = Object.values(autopilot_data.parameters)
        .filter((parameter: Parameter) => !parameter.readonly)
        .sort((first: Parameter, second: Parameter) => {
          parameter_name_max_size = Math.max(parameter_name_max_size, first.name.length)
          parameter_name_max_size = Math.max(parameter_name_max_size, second.name.length)

          if (first.name < second.name) {
            return -1
          }
          if (first.name > second.name) {
            return 1
          }
          return 0
        })

      let content = ''

      const vehicle = autopilot.vehicle_type ?? 'vehicle'
      const platform = autopilot.current_board?.platform ?? 'platform'
      const version = autopilot.firmware_info?.version ?? 'version'
      const type = autopilot.firmware_info?.type ?? 'None'
      const date = format(new Date(), 'yyyyMMdd-HHmmss')

      content += `# Date: ${new Date()}\n`
      content += `# Vehicle: ${vehicle}\n`
      content += `# Platform: ${platform}\n`
      content += `# Version: ${version}-${type}\n\n`
      content += '# Parameters\n'

      const file_name = `${vehicle}-${version}-${type}-${date}`

      for (const param of parameters) {
        // Calculate space between name and value to make it pretty
        const space = Array(parameter_name_max_size - param.name.length + 2).join(' ')
        content += `${param.name}${space}${param.value}\n`
      }

      const file = new File([content], `${file_name}.txt`, { type: 'text/plain' })
      saveAs(file)
    },
    async setParameterFile(file: (File | null)): Promise<void> {
      const content = await file?.text()
      const lines = content?.split(/\r?\n/)
      const new_parameters = lines
        ?.map((line) => line.trim())
        ?.filter((line) => line[0] !== '#' && line.length !== 0)
        ?.map((line) => {
          const [name, value] = line.split(/ {1,}/)
          const type = autopilot_data.parameters.find((param) => param.name === name)?.paramType.type
          return { name, value: parseFloat(value), type }
        })
      this.loaded_parameter = new_parameters ?? []
    },
    applyParameterFile(): void {
      for (const param of this.loaded_parameter) {
        mavlink2rest.setParam(param.name, param.value, param.type)
      }
      this.load_param_dialog = false
    },
  },
})
</script>

<style>
div.v-messages {
  min-height: 1px;
}

.hand-cursor {
  cursor: pointer;
}
</style>
