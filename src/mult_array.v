/*
 * Copyright (c) 2026 Srija Nane
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

// 8x4 array multiplier: operand_a[7:0] x operand_b[3:0] -> product[11:0]
// Partial products are formed by an AND-gate array (one row per operand_b
// bit), then reduced by a ripple of adder rows -- the classic array
// multiplier structure.
module mult_array (
    input  wire [7:0]  operand_a,
    input  wire [3:0]  operand_b,
    output wire [11:0] product
);

  // Partial product rows, each shifted into its bit-weighted position.
  wire [11:0] pp0 = {4'b0, operand_a & {8{operand_b[0]}}};
  wire [11:0] pp1 = {3'b0, operand_a & {8{operand_b[1]}}, 1'b0};
  wire [11:0] pp2 = {2'b0, operand_a & {8{operand_b[2]}}, 2'b0};
  wire [11:0] pp3 = {1'b0, operand_a & {8{operand_b[3]}}, 3'b0};

  // Adder rows summing the shifted partial products.
  wire [11:0] sum01 = pp0 + pp1;
  wire [11:0] sum012 = sum01 + pp2;

  assign product = sum012 + pp3;

endmodule
