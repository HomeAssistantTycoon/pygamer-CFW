/* ----------------------------------------------------------------------------
 *         SAM Software Package License
 * ----------------------------------------------------------------------------
 * Copyright (c) 2011-2014, Atmel Corporation
 *
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following condition is met:
 *
 * Redistributions of source code must retain the above copyright notice,
 * this list of conditions and the disclaimer below.
 *
 * Atmel's name may not be used to endorse or promote products derived from
 * this software without specific prior written permission.
 *
 * DISCLAIMER: THIS SOFTWARE IS PROVIDED BY ATMEL "AS IS" AND ANY EXPRESS OR
 * IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
 * MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT ARE
 * DISCLAIMED. IN NO EVENT SHALL ATMEL BE LIABLE FOR ANY DIRECT, INDIRECT,
 * INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 * LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
 * OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
 * LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
 * NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
 * EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 * ----------------------------------------------------------------------------
 */

/**
 * --------------------
 * SAM-BA Implementation on SAMD21 and SAMD51
 * --------------------
 * Requirements to use SAM-BA :
 *
 * Supported communication interfaces (SAMD21):
 * --------------------
 *
 * SERCOM5 : RX:PB23 TX:PB22
 * Baudrate : 115200 8N1
 *
 * USB : D-:PA24 D+:PA25
 *
 * Pins Usage
 * --------------------
 * The following pins are used by the program :
 * PA25 : input/output
 * PA24 : input/output
 * PB23 : input
 * PB22 : output
 * PA15 : input
 *
 * The application board shall avoid driving the PA25,PA24,PB23,PB22 and PA15
 * signals
 * while the boot program is running (after a POR for example)
 *
 * Clock system
 * --------------------
 * CPU clock source (GCLK_GEN_0) - 48MHz DFLL oscillator (DFLL48M)
 * SERCOM5 core GCLK source (GCLK_ID_SERCOM5_CORE) - GCLK_GEN_0 (i.e., FDLL48M)
 * USB GCLK source (GCLK_ID_USB) - GCLK_GEN_0 (i.e., DFLL in CRM or open loop mode)
 *
 * Crystalless mode:
 * GCLK Generator 0 source (GCLK_GEN_0) - 48MHz DFLL in Clock Recovery mode
 * (DFLL48M)
 *
 * Crytal mode:
 * GCLK Generator 0 source (GCLK_GEN_0) - 48MHz DFLL in closed loop mode
 * GCLK Generator 1 source (GCLK_GEN_1) - 32 kHz external cyrstal (XOSC32K)
 * DFLL48M Refence clock (GCLK_DFLL48M_REF) - GCLK_GEN_1 (i.e., XOSC32K)
 *
 * Memory Mapping
 * --------------------
 * SAM-BA code will be located at 0x0 and executed before any applicative code.
 *
 * Applications compiled to be executed along with the bootloader will start at
 * 0x2000 (samd21) or 0x4000 (samd51)
 *
 */

#include "uf2.h"

static void check_start_application(void);

static volatile bool main_b_cdc_enable = false;
extern int8_t led_tick_step;

#if defined(SAMD21)
    #define RESET_CONTROLLER PM
#elif defined(SAMD51)
    #define RESET_CONTROLLER RSTC
#endif

#if USE_SCREEN
// Forward decls from the screen module (to avoid adding new headers)
extern void screen_print(int x, int y, const char *text);
extern void screen_fill_rect(int x, int y, int w, int h, uint16_t color);
extern int  screen_width(void);
extern int  screen_height(void);

static inline void show_gameslots_label(void) {
    // Draw a small black bar at the bottom and print a white label on it.
    int w = screen_width();
    int h = screen_height();
    int bar_h = 10;
    int pad_x = 4;
    int text_y = h - bar_h + 1;
    screen_fill_rect(0, h - bar_h, w, bar_h, 0x0000); // black footer
    screen_print(pad_x, text_y, "Gameslots ready");
}
#endif

/**
 * \brief Check the application startup condition
 *
 */
static void check_start_application(void) {
    uint32_t app_start_address;

    /* Load the Reset Handler address of the application */
    app_start_address = *(uint32_t *)(APP_START_ADDRESS + 4);

    /**
     * Test reset vector of application @APP_START_ADDRESS+4
     * Sanity check on the Reset_Handler address
     */
    if (app_start_address < APP_START_ADDRESS || app_start_address > FLASH_SIZE) {
        /* Stay in bootloader */
        return;
    }

#if USE_SINGLE_RESET
    if (SINGLE_RESET()) {
        if (RESET_CONTROLLER->RCAUSE.bit.POR || *DBL_TAP_PTR != DBL_TAP_MAGIC_QUICK_BOOT) {
            *DBL_TAP_PTR = DBL_TAP_MAGIC_QUICK_BOOT;
            resetHorizon = timerHigh + 50;
            return;
        }
    }
#endif

    if (RESET_CONTROLLER->RCAUSE.bit.POR) {
        *DBL_TAP_PTR = 0;
    }
    else if (*DBL_TAP_PTR == DBL_TAP_MAGIC) {
        *DBL_TAP_PTR = 0;
        return; // stay in bootloader
    }
    else {
        if (*DBL_TAP_PTR != DBL_TAP_MAGIC_QUICK_BOOT) {
            *DBL_TAP_PTR = DBL_TAP_MAGIC;
            delay(500);
        }
        *DBL_TAP_PTR = 0;
    }

    LED_MSC_OFF();

#if defined(BOARD_RGBLED_CLOCK_PIN)
    RGBLED_set_color(COLOR_LEAVE);
#endif

    __set_MSP(*(uint32_t *)APP_START_ADDRESS);
    SCB->VTOR = ((uint32_t)APP_START_ADDRESS & SCB_VTOR_TBLOFF_Msk);
    asm("bx %0" ::"r"(app_start_address));
}

extern char _etext;
extern char _end;

int main(void) {
    if (SCB->VTOR)
        while (1) {
        }

#if defined(SAMD21)
    // Brownout config for SAMD21 ...
    SYSCTRL->BOD33.bit.ENABLE = 0;
    while (!SYSCTRL->PCLKSR.bit.B33SRDY) {};
    SYSCTRL->BOD33.reg = (SYSCTRL_BOD33_LEVEL(39) |
                          SYSCTRL_BOD33_ACTION_NONE |
                          SYSCTRL_BOD33_HYST);
    SYSCTRL->BOD33.bit.ENABLE = 1;
    while (!SYSCTRL->PCLKSR.bit.BOD33RDY) {}
    while (SYSCTRL->PCLKSR.bit.BOD33DET) {}
    SYSCTRL->BOD33.bit.ENABLE = 0;
    while (!SYSCTRL->PCLKSR.bit.B33SRDY) {};
    SYSCTRL->BOD33.reg |= SYSCTRL_BOD33_ACTION_RESET;
    SYSCTRL->BOD33.bit.ENABLE = 1;
#elif defined(SAMD51)
    WDT->CTRLA.reg = 0;
    while(WDT->SYNCBUSY.reg) {}
    SUPC->BOD33.bit.ENABLE = 0;
    while (!SUPC->STATUS.bit.B33SRDY) {}
    SUPC->BOD33.bit.LEVEL = 200;  
    SUPC->BOD33.bit.ACTION = SUPC_BOD33_ACTION_NONE_Val;
    SUPC->BOD33.bit.ENABLE = 1;
    while (!SUPC->STATUS.bit.BOD33RDY) {}
    while (SUPC->STATUS.bit.BOD33DET) {}
    if (RSTC->RCAUSE.bit.POR || RSTC->RCAUSE.bit.BODVDD) {
        do { delay(100); } while (SUPC->STATUS.bit.BOD33DET);
    }
    SUPC->BOD33.bit.ENABLE = 0;
    while (!SUPC->STATUS.bit.B33SRDY) {}
    SUPC->BOD33.bit.ACTION = SUPC_BOD33_ACTION_RESET_Val;
    SUPC->BOD33.bit.ENABLE = 1;
#endif

#if USB_VID == 0x239a && USB_PID == 0x0013
    delay(15);
#endif
    led_init();

    logmsg("Start");
    assert((uint32_t)&_etext < APP_START_ADDRESS);
    assert(!USE_MONITOR || (uint32_t)&_end < 0x20005000);

    assert(8 << NVMCTRL->PARAM.bit.PSZ == FLASH_PAGE_SIZE);
    assert(FLASH_PAGE_SIZE * NVMCTRL->PARAM.bit.NVMP == FLASH_SIZE);

    check_start_application();

    system_init();
    __DMB();
    __enable_irq();

#if USE_UART
    usart_open();
#endif

    logmsg("Before main loop");

    usb_init();

    RGBLED_set_color(COLOR_START);
    led_tick_step = 10;

    while (1) {
        if (USB_Ok()) {
            if (!main_b_cdc_enable) {
#if USE_SINGLE_RESET
                resetHorizon = 0;
#endif
                RGBLED_set_color(COLOR_USB);
                led_tick_step = 1;

#if USE_SCREEN
                screen_init();
                draw_drag();
                show_gameslots_label();   // 👈 our new line
#endif
            }

            main_b_cdc_enable = true;
        }

#if USE_MONITOR
        if (main_b_cdc_enable) {
            logmsg("entering monitor loop");
            while (1) {
                sam_ba_monitor_run();
            }
        }
#if USE_UART
        if (!main_b_cdc_enable && usart_sharp_received()) {
            RGBLED_set_color(COLOR_UART);
            sam_ba_monitor_init(SAM_BA_INTERFACE_USART);
            while (1) {
                sam_ba_monitor_run();
            }
        }
#endif
#else
        if (main_b_cdc_enable) {
            process_msc();
        }
#endif

        if (!main_b_cdc_enable) {
            for (int i = 1; i < 256; ++i) {
                asm("nop");
            }
        }
    }
}
