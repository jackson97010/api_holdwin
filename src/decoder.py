"""Tick data decoder for Taiwan Stock Exchange data."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import logging
import pandas as pd

logger = logging.getLogger(__name__)


class TickDataDecoder:
    """Decode tick data and label trade direction."""

    NEUTRAL_CODE = "0"

    def __init__(self, market_open_time: str = "09:00:00") -> None:
        self.market_open_time = pd.Timestamp(market_open_time).time()
        logger.info("TickDataDecoder initialized with market open time %s", market_open_time)

    def load_data(self, file_path: str) -> pd.DataFrame:
        logger.info("Loading data from %s", file_path)
        df = pd.read_parquet(file_path)
        logger.info("Loaded %s rows (types: %s)", len(df), df["Type"].value_counts().to_dict())
        return df

    def filter_trading_hours(self, df: pd.DataFrame) -> pd.DataFrame:
        """Keep ticks at or after the designated market open."""
        if not pd.api.types.is_datetime64_any_dtype(df["Datetime"]):
            df["Datetime"] = pd.to_datetime(df["Datetime"])

        time_mask = df["Datetime"].dt.time >= self.market_open_time
        trade_mask = (df["Type"] == "Trade") & time_mask
        depth_mask = (df["Type"] == "Depth") & time_mask
        filtered_df = df[trade_mask | depth_mask].copy()

        logger.info(
            "Filtered to %s rows (trades: %s, depths: %s)",
            len(filtered_df),
            (filtered_df["Type"] == "Trade").sum(),
            (filtered_df["Type"] == "Depth").sum(),
        )
        return filtered_df

    def label_trade_direction(self, df: pd.DataFrame) -> pd.DataFrame:
        """Label trades using the latest depth snapshot at or before the trade time."""
        if df.empty:
            return df

        df = df.sort_values(["Timestamp", "Datetime"]).reset_index(drop=True)
        df["tick_type"] = None

        trade_mask = df["Type"] == "Trade"
        depth_mask = df["Type"] == "Depth"
        trades = df[trade_mask].copy()
        depth = (
            df[depth_mask][["Timestamp", "Bid1_Price", "Ask1_Price"]]
            .rename(columns={"Bid1_Price": "Depth_Bid1", "Ask1_Price": "Depth_Ask1"})
            .copy()
        )

        if trades.empty or depth.empty:
            logger.warning("Insufficient trades or depth rows for labeling.")
            return df

        trades["original_index"] = trades.index
        depth = depth.sort_values("Timestamp")
        trades_sorted = trades.sort_values("Timestamp")

        merged = pd.merge_asof(
            trades_sorted,
            depth,
            on="Timestamp",
            direction="backward",
            suffixes=("", "_depth"),
        )

        merged["tick_type"] = None
        price = merged["Price"]
        bid = merged["Depth_Bid1"]
        ask = merged["Depth_Ask1"]

        buy_mask = (ask.notna()) & (price >= ask)
        sell_mask = (bid.notna()) & (price <= bid)
        merged.loc[buy_mask, "tick_type"] = "1"
        merged.loc[~buy_mask & sell_mask, "tick_type"] = "2"

        unresolved = merged["tick_type"].isna()
        for idx, row in merged[unresolved].iterrows():
            price_val = row["Price"]
            bid_val = row["Depth_Bid1"]
            ask_val = row["Depth_Ask1"]

            if pd.notna(ask_val) and pd.notna(bid_val):
                if abs(price_val - ask_val) <= abs(price_val - bid_val):
                    merged.at[idx, "tick_type"] = "1"
                else:
                    merged.at[idx, "tick_type"] = "2"
            elif pd.notna(ask_val):
                merged.at[idx, "tick_type"] = "1"
            elif pd.notna(bid_val):
                merged.at[idx, "tick_type"] = "2"

        for _, row in merged.dropna(subset=["tick_type"]).iterrows():
            df.at[row["original_index"], "tick_type"] = row["tick_type"]

        logger.info(
            "Trade direction labeling summary: %s",
            merged["tick_type"].value_counts().to_dict(),
        )
        return df

    def process(self, input_path: str, output_path: Optional[str] = None) -> pd.DataFrame:
        logger.info("Starting decoder pipeline")
        df = self.load_data(input_path)
        df = self.filter_trading_hours(df)
        df = self.label_trade_direction(df)

        if output_path:
            logger.info("Saving processed parquet to %s", output_path)
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(output_path, index=False)

        self._print_summary(df)
        return df

    def _print_summary(self, df: pd.DataFrame) -> None:
        logger.info("=" * 50)
        logger.info("PROCESSED SUMMARY")
        logger.info("=" * 50)
        logger.info("Total rows: %s", len(df))
        if df.empty:
            return
        trade_df = df[df["Type"] == "Trade"]
        logger.info("Total trades: %s", len(trade_df))
        if not trade_df.empty:
            logger.info("tick_type distribution: %s", trade_df["tick_type"].value_counts().to_dict())
        logger.info("=" * 50)


def main() -> None:
    decoder = TickDataDecoder()
    input_file = "C:\\Users\\tacor\\Documents\\_04_strategy\\data\\20251118\\3167.parquet"
    output_file = "C:\\Users\\tacor\\Documents\\_04_strategy\\output\\3167_20251118_processed.parquet"
    decoder.process(input_file, output_file)


if __name__ == "__main__":
    main()
