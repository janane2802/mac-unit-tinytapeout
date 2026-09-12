/*
 * Copyright (c) 2026 Srija Nane
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module tt_um_janane2802_mac_unit (
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
    input  wire       ena,      // always 1 when the design is powered, so you can ignore it
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);

  // Pinout:
  //   ui_in[7:0]  = operand_a[7:0]
  //   uio_in[0]   = mac_enable
  //   uio_in[1]   = acc_clear
  //   uio_out[2]  = overflow (output)
  //   uio_in[3]   = byte_select (0 = low byte, 1 = high byte)
  //   uio_in[7:4] = operand_b[3:0]
  //   uo_out[7:0] = selected accumulator byte

  wire [7:0]  operand_a   = ui_in;
  wire        mac_enable  = uio_in[0];
  wire        acc_clear   = uio_in[1];
  wire        byte_select = uio_in[3];
  wire [3:0]  operand_b   = uio_in[7:4];

  wire [11:0] product;
  wire [15:0] acc;
  wire        overflow;

  mult_array mult_inst (
      .operand_a(operand_a),
      .operand_b(operand_b),
      .product  (product)
  );

  mac_accumulator acc_inst (
      .clk       (clk),
      .rst_n     (rst_n),
      .mac_enable(mac_enable),
      .acc_clear (acc_clear),
      .product   (product),
      .acc       (acc),
      .overflow  (overflow)
  );

  assign uo_out = byte_select ? acc[15:8] : acc[7:0];

  // uio[2] is the only bidir pin driven as an output; the rest are inputs.
  assign uio_out = {5'b0, overflow, 2'b0};
  assign uio_oe  = 8'b0000_0100;

  // List all unused inputs to prevent warnings
  wire _unused = &{ena, uio_in[2], 1'b0};

endmodule
