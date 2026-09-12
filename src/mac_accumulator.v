/*
 * Copyright (c) 2026 Srija Nane
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

// 16-bit accumulator for the MAC unit.
// - acc_clear takes priority over mac_enable when both are asserted.
// - mac_enable adds `product` into the running total.
// - overflow latches high whenever an addition carries out past bit 15,
//   and stays high until the next mac_enable that does not overflow, or
//   until acc_clear.
module mac_accumulator (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        mac_enable,
    input  wire        acc_clear,
    input  wire [11:0] product,
    output reg  [15:0] acc,
    output reg         overflow
);

  wire [16:0] sum = {1'b0, acc} + {5'b0, product};

  always @(posedge clk) begin
    if (!rst_n) begin
      acc      <= 16'd0;
      overflow <= 1'b0;
    end else if (acc_clear) begin
      acc      <= 16'd0;
      overflow <= 1'b0;
    end else if (mac_enable) begin
      acc      <= sum[15:0];
      overflow <= sum[16];
    end
  end

endmodule
