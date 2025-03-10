<template>
  <div>
    <v-row class="mt-5">
      <v-col
        cols="12"
        sm="8"
      >
        <v-card>
          <vehicle-viewer :highlight="highlight" :transparent="true" :autorotate="false" />
        </v-card>
        <v-card class="mt-3">
          <v-simple-table
            dense
          >
            <template #default>
              <thead>
                <tr>
                  <th class="text-left subtitle-1 font-weight-bold">
                    Motor Test
                  </th>
                  <th>
                    <v-switch
                      v-model="desired_armed_state"
                      :loading="desired_armed_state !== is_armed ? 'warning' : null"
                      class="mx-1 flex-grow-0"
                      :label="`${is_armed ? 'Armed' : 'Disarmed'}`"
                      :color="`${is_armed ? 'error' : 'success'}`"
                      @change="desired_armed_state ? arm() : disarm()"
                    />
                  </th>
                  <th />
                </tr>
              </thead>
              <tbody class="align-center">
                <tr
                  v-for="motor of available_motors"
                  :key="'mot' + motor"
                  width="100%"
                  height="65"
                  class="ma-0 pa-0"
                  @mouseover="highlight = [`Motor${motor}`]"
                  @mouseleave="highlight = default_highlight"
                >
                  <td width="20%">
                    {{ `Motor ${motor}` }}
                  </td>
                  <td width="80%">
                    <v-slider
                      v-model="motor_targets[motor]"
                      class="align-center"
                      :min="1000"
                      :max="2000"
                      hide-details
                      thumb-label
                      color="primary"
                      track-color="primary"
                      :disabled="!is_armed"
                      @mouseup="restart_motor_zeroer()"
                      @mousedown="pause_motor_zeroer()"
                    />
                    <div
                      class="v-progress-linear"
                      style="height: 25px;"
                    >
                      <div
                        class="pwm-bar-bg"
                      />
                      <div
                        class="pwm-bar"
                        :style="styleForMotorBar(motor_outputs[motor])"
                      />
                      <div class="pwm-bar-content">
                        <strong>{{ (motor_outputs[motor] - 1500) / 10 }}%</strong>
                      </div>
                    </div>
                  </td>
                </tr>
              </tbody>
            </template>
          </v-simple-table>
        </v-card>
      </v-col>
      <v-col
        cols="12"
        sm="4"
      >
        <v-card>
          <v-simple-table>
            <template #default>
              <thead>
                <tr>
                  <th class="text-left">
                    Name
                  </th>
                  <th class="text-left">
                    Value
                  </th>
                  <th class="text-left">
                    Output
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(item, index) in servo_function_parameters"
                  :key="item.name"
                  style="cursor: pointer;"
                  @mouseover="highlight = [stringToUserFriendlyText(printParam(item))]"
                  @mouseleave="highlight = default_highlight"
                  @click="showParamEdit(item)"
                >
                  <td>{{ item.name }}</td>
                  <td>{{ stringToUserFriendlyText(printParam(item)) }}</td>
                  <td>{{ servo_output[index] }}</td>
                </tr>
              </tbody>
            </template>
          </v-simple-table>
        </v-card>
      </v-col>
    </v-row>
    <parameter-editor-dialog
      v-model="edit_param_dialog"
      :param="param"
    />
  </div>
</template>

<script lang="ts">
import Vue from 'vue'

import ParameterEditorDialog from '@/components/parameter-editor/ParameterEditorDialog.vue'
import VehicleViewer from '@/components/vehiclesetup/viewers/VehicleViewer.vue'
import mavlink2rest from '@/libs/MAVLink2Rest'
import { MavCmd, MavModeFlag } from '@/libs/MAVLink2Rest/mavlink2rest-ts/messages/mavlink2rest-enum'
import autopilot_data from '@/store/autopilot'
import autopilot from '@/store/autopilot_manager'
import mavlink from '@/store/mavlink'
import Parameter, { printParam } from '@/types/autopilot/parameter'
import { SERVO_FUNCTION } from '@/types/autopilot/parameter-sub-enums'
import { Dictionary } from '@/types/common'
import mavlink_store_get from '@/utils/mavlink'

const param_value_map = {
  Submarine: {
    RCIN8: 'Lights 1',
    RCIN9: 'Lights 2',
    RCIN10: 'Video Switch',
  },
} as Dictionary<Dictionary<string>>

export default Vue.extend({
  name: 'PwmSetup',
  components: {
    ParameterEditorDialog,
    VehicleViewer,
  },
  data() {
    return {
      highlight: ['Motor', 'Light', 'Mount', 'Gripper'],
      default_highlight: ['Motor', 'Light', 'Mount', 'Gripper'],
      edit_param_dialog: false,
      param: undefined as Parameter | undefined,
      motor_targets: {} as {[key: number]: number},
      motor_zeroer_interval: undefined as undefined | number,
      motor_writer_interval: undefined as undefined | number,
      desired_armed_state: false,
      arming_timeout: undefined as number | undefined,
    }
  },
  computed: {
    servo_function_parameters(): Parameter[] {
      const params = autopilot_data.parameterRegex('^SERVO(\\d+)_FUNCTION$')
      // Sort parameters using the servo number instead of alphabetically
      const sorted = params.sort(
        (a: Parameter, b: Parameter) => a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' }),
      )
      return sorted
    },
    vehicle_type() {
      return autopilot.vehicle_type
    },
    available_motors(): number[] {
      return this.servo_function_parameters.filter(
        (parameter) => parameter.value >= SERVO_FUNCTION.MOTOR1 && parameter.value <= SERVO_FUNCTION.MOTOR8,
      ).map((parameter) => parseInt(/\d+/g.exec(printParam(parameter))?.[0] ?? '0', 10))
    },
    is_armed(): boolean {
      // This should be a getter at mavlink store. but that wasn't reactive
      const mode = mavlink_store_get(mavlink, 'HEARTBEAT.messageData.message.base_mode.bits') as number
      const armed_flag = MavModeFlag.MAV_MODE_FLAG_SAFETY_ARMED as number
      return (mode & armed_flag) === armed_flag
    },
    motor_outputs() : {[key: number]: number} {
      const data = mavlink_store_get(mavlink, 'SERVO_OUTPUT_RAW.messageData.message') as Dictionary<number>
      const new_data = {} as {[key: number]: number}
      if (!data) {
        return {}
      }
      for (const [key, value] of Object.entries(data)) {
        if (!key.includes('servo')) continue
        const motor_name = parseInt(key.replace('servo', '').replace('_raw', ''), 10)
        new_data[motor_name] = value
      }
      return new_data
    },
    servo_output(): number[] {
      const output = Array(16)
        .fill(0)
      const data = mavlink_store_get(mavlink, 'SERVO_OUTPUT_RAW.messageData.message') as Dictionary<number> | undefined
      if (!data) {
        return output
      }
      return output
        .map((_, i) => data[`servo${i + 1}_raw`])
    },
  },
  mounted() {
    this.motor_zeroer_interval = setInterval(this.zero_motors, 300)
    this.motor_writer_interval = setInterval(this.write_motors, 100)
    mavlink.setMessageRefreshRate({ messageName: 'SERVO_OUTPUT_RAW', refreshRate: 10 })
    this.desired_armed_state = this.is_armed
  },
  beforeDestroy() {
    clearInterval(this.motor_zeroer_interval)
    clearInterval(this.motor_writer_interval)
    mavlink.setMessageRefreshRate({ messageName: 'SERVO_OUTPUT_RAW', refreshRate: 1 })
  },
  methods: {
    styleForMotorBar(value: number): string {
      const percent = (value - 1500) / 10
      const left = percent < 0 ? 50 + percent : 50
      return `width: ${Math.abs(percent)}%; left: ${left}%; background-color: red`
    },
    showParamEdit(param: Parameter) {
      this.param = param
      this.edit_param_dialog = true
    },
    stringToUserFriendlyText(text: string) {
      return param_value_map?.[this.vehicle_type ?? '']?.[text] ?? text
    },
    printParam,
    zero_motors() {
      for (const motor of this.available_motors) {
        this.motor_targets[motor] = 1500
      }
    },
    async write_motors() {
      if (this.is_armed && this.desired_armed_state) {
        for (const [motor, value] of Object.entries(this.motor_targets)) {
          this.doMotorTest(parseInt(motor, 10), value)
        }
      }
    },
    restart_motor_zeroer() {
      clearInterval(this.motor_zeroer_interval)
      this.motor_zeroer_interval = setInterval(this.zero_motors, 500)
    },
    pause_motor_zeroer() {
      clearInterval(this.motor_zeroer_interval)
    },
    arm() {
      this.armDisarm(true, true)
      this.arming_timeout = setTimeout(() => {
        if (this.desired_armed_state === this.is_armed) return
        this.desired_armed_state = this.is_armed
        console.warn('Arming failed!')
      }, 5000)
    },
    disarm() {
      this.armDisarm(false, true)
      this.arming_timeout = setTimeout(() => {
        if (this.desired_armed_state === this.is_armed) return
        this.desired_armed_state = this.is_armed
        console.warn('Disarming failed!')
      }, 5000)
    },
    armDisarm(arm: boolean, force: boolean): void {
      mavlink2rest.sendMessage(
        {
          header: {
            system_id: 255,
            component_id: 0,
            sequence: 0,
          },
          message: {
            type: 'COMMAND_LONG',
            param1: arm ? 1 : 0, // 0: Disarm, 1: ARM,
            param2: force ? 21196 : 0, // force arming/disarming (override preflight checks and disarming in flight)
            param3: 0,
            param4: 0,
            param5: 0,
            param6: 0,
            param7: 0,
            command: {
              type: MavCmd.MAV_CMD_COMPONENT_ARM_DISARM,
            },
            target_system: autopilot_data.system_id,
            target_component: 1,
            confirmation: 0,
          },
        },
      )
    },
    async doMotorTest(motorId: number, output: number): Promise<void> {
      mavlink2rest.sendMessageViaWebsocket(
        {
          header: {
            system_id: 255,
            component_id: 0,
            sequence: 0,
          },
          message: {
            type: 'COMMAND_LONG',
            param1: motorId - 1,
            param2: 1, // MOTOR_TEST_THROTTLE_PWM
            param3: output,
            param4: 1, // Seconds running the motor
            param5: 1, // Number of motors to be tested
            param6: 2, // Motor numbers are specified as the output as labeled on the board.
            param7: 0,
            command: {
              type: MavCmd.MAV_CMD_DO_MOTOR_TEST,
            },
            target_system: autopilot_data.system_id,
            target_component: 1,
            confirmation: 0,
          },
        },
      )
    },
  },
})
</script>
<style>
.pwm-bar-content {
  align-items: center;
  display: flex;
  height: 100%;
  left: 0;
  justify-content: center;
  position: absolute;
  top: 0;
  width: 100%;
}

.pwm-bar {
    /* eslint-disable-next-line */
    background-image: linear-gradient(135deg, rgba(255, 255, 255, 0.25) 25%, transparent 0, transparent 50%,
      rgba(255, 255, 255, 0.25) 0, rgba(255, 255, 255, 0.25) 75%, transparent 0, transparent);
    background-size: 40px 40px;
    background-repeat: repeat;
    height: inherit;
    left: 0;
    position: absolute;
    transition: none;
}
.pwm-bar-bg {
  bottom: 0;
  left: 0;
  position: absolute;
  top: 0;
  transition: inherit;
  opacity: 0.3;
  width: 100%;
  background-color: rgb(195, 195, 195);
}
/* Disable transition on v-slider thumb */
.v-slider__thumb-container {
  transition:none !important;
}
</style>
