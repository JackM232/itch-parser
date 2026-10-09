module itch_parser (
    input  logic        clk,
    input  logic        rst,        // synchronous, active-high

    // Byte stream in: a byte transfers on cycles where in_valid is 1
    input  logic        in_valid,
    output logic        in_ready,
    input  logic [7:0]  in_data,

    // Decoded Add Order out: out_valid is high for 1 cycle per order
    output logic        out_valid,
    output logic [15:0] out_stock_locate,
    output logic [15:0] out_tracking,
    output logic [47:0] out_timestamp,
    output logic [63:0] out_order_ref,
    output logic [7:0]  out_side,
    output logic [31:0] out_shares,
    output logic [63:0] out_stock,
    output logic [31:0] out_price
);

    logic [15:0] msg_len;
    logic [15:0] idx;
    logic last_byte;
    logic is_add;
    

    typedef enum logic [1:0] {LEN_HI, LEN_LO, BODY} state_t;
    state_t state, next_state;

    assign last_byte = (state == BODY) && (idx == msg_len - 1);
    assign in_ready = 1'b1;

    always_comb begin
        next_state = state;
        if (in_valid) begin
            case (state)
                LEN_HI: next_state = LEN_LO;
                LEN_LO: next_state = BODY;
                BODY: if (last_byte) next_state = LEN_HI;
            endcase
        end
    end

    // State Handler
    always_ff @(posedge clk) begin
        if (rst) 
            state <= LEN_HI;
        else
            state <= next_state;
    end

    always_ff @(posedge clk) begin
        if (rst)
            out_valid <= 1'd0;
        else 
            out_valid <= in_valid && is_add && last_byte;
    end

    always_ff @(posedge clk) begin

        if (in_valid) begin    
            case (state)
                LEN_HI: msg_len <= {in_data, msg_len[7:0]};
                LEN_LO: begin
                    msg_len <= {msg_len[15:8], in_data};
                    idx <= 0;
                end
                BODY: begin

                    idx <= idx + 1;
                    if (idx == 0)
                        is_add <= in_data == 8'h41 ? 1 : 0;
                    if (idx >= 1 && idx <= 2)
                        out_stock_locate <= {out_stock_locate[7:0], in_data};
                    if (idx >= 3 && idx <= 4)
                        out_tracking <= {out_tracking[7:0], in_data};
                    if (idx >= 5 && idx <= 10)
                        out_timestamp <= {out_timestamp[39:0], in_data};
                    if (idx >= 11 && idx <= 18)
                        out_order_ref <= {out_order_ref[55:0], in_data};
                    if (idx == 19)
                        out_side <= in_data;
                    if (idx >= 20 && idx <= 23)
                        out_shares <= {out_shares[23:0], in_data};
                    if (idx >= 24 && idx <= 31)
                        out_stock <= {out_stock[55:0], in_data};
                    if (idx >= 32 && idx <= 35)
                        out_price <= {out_price[23:0], in_data};
                end
            endcase
        end
    end 
endmodule