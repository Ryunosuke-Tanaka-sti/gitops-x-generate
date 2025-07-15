#!/usr/bin/env python3

"""
Claude API 簡易テストスクリプト

このスクリプトは、Claude APIの基本的な機能をテストし、
メタデータの取得方法を確認するためのものです。

主な機能:
- Claude APIの基本的な呼び出し
- レスポンスメタデータの取得
- トークン使用量の計算
- 料金計算

使用方法:
    export ANTHROPIC_API_KEY="your-api-key"
    python claude_api_test.py

Author: Claude API Test
Version: 1.0.0
License: MIT
"""

import os
import json
from datetime import datetime
from typing import Any, Dict

try:
    from anthropic import Anthropic
except ImportError:
    print("❌ anthropic パッケージがインストールされていません")
    print("pip install anthropic でインストールしてください")
    exit(1)


class ClaudeAPITester:
    """
    Claude API の基本機能をテストするクラス
    """

    def __init__(self):
        """
        初期化処理
        """
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY 環境変数が設定されていません")

        self.client = Anthropic(api_key=self.api_key)

        # 料金設定（2025年7月時点）
        self.pricing = {
            "claude-3-7-sonnet-20241022": {
                "input_per_million": 3.00,
                "output_per_million": 15.00,
                "cache_write_per_million": 3.75,
                "cache_read_per_million": 0.30,
            },
            "claude-3-5-sonnet-20241022": {
                "input_per_million": 3.00,
                "output_per_million": 15.00,
                "cache_write_per_million": 3.75,
                "cache_read_per_million": 0.30,
            },
            "claude-3-5-haiku-20241022": {
                "input_per_million": 0.80,
                "output_per_million": 4.00,
                "cache_write_per_million": 1.00,
                "cache_read_per_million": 0.08,
            },
        }

    def test_basic_message(
        self, model: str = "claude-3-5-sonnet-20241022"
    ) -> Dict[str, Any]:
        """
        基本的なメッセージ送信テスト

        Args:
            model (str): 使用するモデル名

        Returns:
            Dict[str, Any]: テスト結果
        """
        print(f"🔄 基本メッセージテスト開始 (モデル: {model})")

        try:
            response = self.client.messages.create(
                model=model,
                max_tokens=1000,
                messages=[
                    {"role": "user", "content": "Hello! Please tell me a short joke."}
                ],
            )

            # メタデータの抽出
            metadata = self._extract_metadata(response)

            print("✅ 基本メッセージテスト成功")
            return {
                "success": True,
                "response_content": response.content[0].text,
                "metadata": metadata,
                "raw_response": response,
            }

        except Exception as e:
            print(f"❌ 基本メッセージテストエラー: {e}")
            return {"success": False, "error": str(e), "error_type": type(e).__name__}

    def test_with_system_prompt(
        self, model: str = "claude-3-5-sonnet-20241022"
    ) -> Dict[str, Any]:
        """
        システムプロンプト付きメッセージテスト

        Args:
            model (str): 使用するモデル名

        Returns:
            Dict[str, Any]: テスト結果
        """
        print(f"🔄 システムプロンプトテスト開始 (モデル: {model})")

        system_prompt = """
        あなたは技術記事のX投稿文を生成するAIアシスタントです。
        以下の条件で投稿文を作成してください：
        - 260文字以内
        - エンジニア向け
        - 技術的な内容を含む
        - 適切なハッシュタグを付ける
        """

        try:
            response = self.client.messages.create(
                model=model,
                max_tokens=1000,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": "PythonでAPIを作成する記事について、効果的なX投稿文を作成してください。",
                    }
                ],
            )

            # メタデータの抽出
            metadata = self._extract_metadata(response)

            print("✅ システムプロンプトテスト成功")
            return {
                "success": True,
                "response_content": response.content[0].text,
                "metadata": metadata,
                "raw_response": response,
            }

        except Exception as e:
            print(f"❌ システムプロンプトテストエラー: {e}")
            return {"success": False, "error": str(e), "error_type": type(e).__name__}

    def test_prompt_caching(
        self, model: str = "claude-3-5-sonnet-20241022"
    ) -> Dict[str, Any]:
        """
        プロンプトキャッシュテスト

        Args:
            model (str): 使用するモデル名

        Returns:
            Dict[str, Any]: テスト結果
        """
        print(f"🔄 プロンプトキャッシュテスト開始 (モデル: {model})")

        # 長めのシステムプロンプト（キャッシュ用）
        long_system_prompt = """
あなたは技術記事のX投稿文を生成するAIアシスタントです。
以下の条件で投稿文を作成してください：
- 260文字以内
- エンジニア向け
- 技術的な内容を含む
- 適切なハッシュタグを付ける
- リンクカードが表示されるようにURLを先頭に配置
---
技術分野別の推奨ハッシュタグ：
- Python: #Python #プログラミング #開発
- JavaScript: #JavaScript #フロントエンド #Web開発
- AI/ML: #AI #機械学習 #人工知能
- インフラ: #インフラ #AWS #クラウド
- データ: #データ分析 #BigData #Analytics
---
投稿パターン：
1. 効果重視・数値訴求型
2. 課題共感・解決提案型
3. 技術トレンド・学習促進型
---
これらの情報を基に、最適な投稿文を生成してください。
        """

        try:
            response = self.client.messages.create(
                model=model,
                max_tokens=1000,
                system=[
                    {
                        "type": "text",
                        "text": long_system_prompt,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[
                    {
                        "role": "user",
                        "content": "Docker と Kubernetes の記事について、効果的なX投稿文を作成してください。",
                    }
                ],
            )

            # メタデータの抽出
            metadata = self._extract_metadata(response)

            print("✅ プロンプトキャッシュテスト成功")
            return {
                "success": True,
                "response_content": response.content[0].text,
                "metadata": metadata,
                "raw_response": response,
            }

        except Exception as e:
            print(f"❌ プロンプトキャッシュテストエラー: {e}")
            return {"success": False, "error": str(e), "error_type": type(e).__name__}

    def _extract_metadata(self, response) -> Dict[str, Any]:
        """
        レスポンスからメタデータを抽出

        Args:
            response: Claude APIのレスポンス

        Returns:
            Dict[str, Any]: 抽出されたメタデータ
        """
        metadata = {
            "response_id": response.id,
            "model": response.model,
            "stop_reason": response.stop_reason,
            "stop_sequence": response.stop_sequence,
            "usage": {},
            "costs": {},
        }

        # 使用量情報の抽出
        if hasattr(response, "usage") and response.usage:
            usage = response.usage
            metadata["usage"] = {
                "input_tokens": getattr(usage, "input_tokens", 0),
                "output_tokens": getattr(usage, "output_tokens", 0),
                "cache_creation_input_tokens": getattr(
                    usage, "cache_creation_input_tokens", 0
                ),
                "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", 0),
            }

            # 料金計算
            costs = self._calculate_costs(response.model, metadata["usage"])
            metadata["costs"] = costs

        return metadata

    def _calculate_costs(self, model: str, usage: Dict[str, int]) -> Dict[str, float]:
        """
        料金計算

        Args:
            model (str): 使用モデル名
            usage (Dict[str, int]): 使用量情報

        Returns:
            Dict[str, float]: 料金情報
        """
        if model not in self.pricing:
            return {"error": f"Unknown model: {model}"}

        prices = self.pricing[model]

        input_cost = usage["input_tokens"] * prices["input_per_million"] / 1000000
        output_cost = usage["output_tokens"] * prices["output_per_million"] / 1000000
        cache_write_cost = (
            usage["cache_creation_input_tokens"]
            * prices["cache_write_per_million"]
            / 1000000
        )
        cache_read_cost = (
            usage["cache_read_input_tokens"]
            * prices["cache_read_per_million"]
            / 1000000
        )

        total_cost = input_cost + output_cost + cache_write_cost + cache_read_cost

        return {
            "input_cost": input_cost,
            "output_cost": output_cost,
            "cache_write_cost": cache_write_cost,
            "cache_read_cost": cache_read_cost,
            "total_cost": total_cost,
            "total_cost_jpy": total_cost * 150,  # 1USD=150JPY想定
        }

    def run_all_tests(
        self, model: str = "claude-3-5-sonnet-20241022"
    ) -> Dict[str, Any]:
        """
        すべてのテストを実行

        Args:
            model (str): 使用するモデル名

        Returns:
            Dict[str, Any]: 全テスト結果
        """
        print("🚀 Claude API テスト開始")
        print("=" * 50)

        results = {
            "test_timestamp": datetime.now().isoformat(),
            "model": model,
            "tests": {},
        }

        # 基本メッセージテスト
        results["tests"]["basic_message"] = self.test_basic_message(model)
        print()

        # システムプロンプトテスト
        results["tests"]["system_prompt"] = self.test_with_system_prompt(model)
        print()

        # プロンプトキャッシュテスト
        results["tests"]["prompt_caching"] = self.test_prompt_caching(model)
        print()

        # 結果サマリー
        successful_tests = sum(
            1 for test in results["tests"].values() if test["success"]
        )
        total_tests = len(results["tests"])

        print("📊 テスト結果サマリー")
        print(f"成功: {successful_tests}/{total_tests}")

        if successful_tests > 0:
            total_input_tokens = sum(
                test["metadata"]["usage"]["input_tokens"]
                for test in results["tests"].values()
                if test["success"] and "metadata" in test
            )
            total_output_tokens = sum(
                test["metadata"]["usage"]["output_tokens"]
                for test in results["tests"].values()
                if test["success"] and "metadata" in test
            )
            total_cost = sum(
                test["metadata"]["costs"]["total_cost"]
                for test in results["tests"].values()
                if test["success"]
                and "metadata" in test
                and "costs" in test["metadata"]
            )

            print(f"総入力トークン: {total_input_tokens:,}")
            print(f"総出力トークン: {total_output_tokens:,}")
            print(f"総コスト: ${total_cost:.6f} (約{total_cost*150:.2f}円)")

        return results

    def save_results(
        self, results: Dict[str, Any], filename: str = "claude_api_test_results.json"
    ):
        """
        テスト結果をファイルに保存

        Args:
            results (Dict[str, Any]): テスト結果
            filename (str): 保存ファイル名
        """
        try:
            # raw_responseは保存から除外（シリアライズできないため）
            clean_results = self._clean_results_for_json(results)

            with open(filename, "w", encoding="utf-8") as f:
                json.dump(clean_results, f, ensure_ascii=False, indent=2)

            print(f"✅ テスト結果を保存しました: {filename}")

        except Exception as e:
            print(f"❌ テスト結果保存エラー: {e}")

    def _clean_results_for_json(self, obj):
        """
        JSONシリアライズ用にオブジェクトをクリーンアップ
        """
        if isinstance(obj, dict):
            return {
                k: self._clean_results_for_json(v)
                for k, v in obj.items()
                if k != "raw_response"
            }
        elif isinstance(obj, list):
            return [self._clean_results_for_json(item) for item in obj]
        else:
            return obj


def main():
    """
    メイン実行関数
    """
    try:
        tester = ClaudeAPITester()

        # 使用するモデルを指定
        model = "claude-3-5-sonnet-20241022"

        # すべてのテストを実行
        results = tester.run_all_tests(model)

        # 結果をファイルに保存
        tester.save_results(results)

        print("\n🎉 テスト完了!")

    except Exception as e:
        print(f"❌ テスト実行エラー: {e}")
        exit(1)


if __name__ == "__main__":
    main()
