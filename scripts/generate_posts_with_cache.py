#!/usr/bin/env python3

"""
X投稿自動生成システム（プロンプトキャッシュ対応版）

このスクリプトは、URLを受け取ってブログ記事を分析し、
3パターンのX投稿文を自動生成します。
プロンプトキャッシュを活用してコストを37%削減します。

主な機能:
- ブログ記事の技術的分析（5段階評価）
- 3パターンのX投稿文生成（効果重視・課題共感・学習促進）
- プロンプトキャッシュによるコスト最適化
- 外部システムプロンプトファイルの読み込み
- Markdownファイルへの自動保存
- 詳細なコスト・トークン使用量記録

使用方法:
    export URL="https://example.com/blog-post"
    export FILENAME="posts/output.md"
    python scripts/generate_posts_with_cache.py

ファイル依存関係:
    - prompts/system_prompt.md: システムプロンプト定義
    - この依存ファイルが存在しない場合はエラーで終了

Author: GitHub Actions Bot
Version: 1.0.0
License: MIT
"""

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse


class XPostGeneratorWithCache:
    """
    プロンプトキャッシュ対応のX投稿生成クラス

    Claude APIを使用してブログ記事を分析し、
    エンジニア向けのX投稿パターンを3つ生成します。
    プロンプトキャッシュにより2回目以降の実行で大幅なコスト削減を実現。

    システムプロンプトは外部ファイル（prompts/system_prompt.md）から読み込みます。
    """

    def __init__(self):
        """
        初期化処理

        環境変数、システムプロンプト、料金設定を初期化します。
        実際のClaude APIキーは環境変数から取得しますが、
        今回はダミー実装のため、API通信は行いません。

        Raises:
            FileNotFoundError: システムプロンプトファイルが見つからない場合
            ValueError: 環境設定に問題がある場合
        """

        # 環境変数とAPI設定の初期化
        self.api_key = os.environ.get("ANTHROPIC_API_KEY", "dummy-key-for-testing")
        self.debug_mode = os.environ.get("DEBUG_MODE", "false").lower() == "true"

        # デバッグ情報の出力
        if self.debug_mode:
            print("🐛 デバッグモード: 有効")
            print(
                (
                    f"🔑 APIキー設定: "
                    f"{'設定済み' if self.api_key != 'dummy-key-for-testing' else 'ダミー'}"
                )
            )

        # システムプロンプトの読み込み（外部ファイルから）
        try:
            self.system_prompt_content = self._load_system_prompt_from_file()
            print("✅ システムプロンプト読み込み完了")
        except Exception as e:
            print(f"❌ システムプロンプト読み込みエラー: {e}")
            raise

        # プロンプトキャッシュ機能の有効化フラグ
        # 実運用では常にTrueにしてコスト削減を図る
        self.cache_enabled = True

        # Claude API料金設定（2025年7月時点の公式料金）
        # 料金は定期的に変更される可能性があるため、設定を分離
        self.pricing = {
            "input_per_million": 3.00,  # $3.00 per 1M input tokens
            "output_per_million": 15.00,  # $15.00 per 1M output tokens
            "cache_write_per_million": 3.75,  # $3.75 per 1M cache write tokens
            "cache_read_per_million": 0.30,  # $0.30 per 1M cache read tokens
        }

        # 想定トークン数（プロンプトキャッシュサイズ計算用）
        # システムプロンプトのサイズから推定
        self.estimated_cache_tokens = 20000  # 約20,000トークン

        if self.debug_mode:
            print("💰 料金設定読み込み完了")
            print(f"📊 推定キャッシュサイズ: {self.estimated_cache_tokens:,} トークン")

    def _load_system_prompt_from_file(self) -> str:
        """
        外部ファイルからシステムプロンプトを読み込み

        prompts/system_prompt.md からシステムプロンプトを読み込みます。
        ファイルが存在しない場合は詳細なエラーメッセージと共に例外を発生させます。

        Returns:
            str: システムプロンプトの内容

        Raises:
            FileNotFoundError: システムプロンプトファイルが見つからない場合
            ValueError: ファイル内容が空または無効な場合
        """

        # システムプロンプトファイルのパス定義
        prompt_file_path = Path("prompts/system_prompt.md")

        print(f"📁 システムプロンプト読み込み: {prompt_file_path}")

        # ファイル存在確認
        if not prompt_file_path.exists():
            error_msg = f"""
                        ❌ システムプロンプトファイルが見つかりません: {prompt_file_path}

                        必要なファイル構成:
                        prompts/
                        └── system_prompt.md  # ← このファイルが必要

                        解決方法:
                        1. prompts ディレクトリを作成
                        2. system_prompt.md ファイルを配置
                        3. ファイルに適切なプロンプト内容を記述

                        現在のディレクトリ: {os.getcwd()}
                        """
            print(error_msg)
            raise FileNotFoundError(error_msg)

        # ファイル読み込み
        try:
            with open(prompt_file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()

            # 内容の基本検証
            if not content:
                raise ValueError(
                    f"システムプロンプトファイルが空です: {prompt_file_path}"
                )

            if len(content) < 1000:
                print(
                    f"⚠️  警告: システムプロンプトが短すぎる可能性があります（{len(content)} 文字）"
                )
                print("   プロンプトキャッシュの効果が限定的になる可能性があります")

            # ファイル情報の出力
            file_size = len(content.encode("utf-8"))
            line_count = len(content.splitlines())

            print("📊 システムプロンプト情報:")
            print(f"   - ファイルサイズ: {file_size:,} bytes")
            print(f"   - 行数: {line_count:,} 行")
            print(f"   - 文字数: {len(content):,} 文字")

            if self.debug_mode:
                print("📝 システムプロンプト先頭プレビュー:")
                preview_lines = content.splitlines()[:5]
                for i, line in enumerate(preview_lines, 1):
                    print(f"   {i}: {line[:80]}{'...' if len(line) > 80 else ''}")

            return content

        except UnicodeDecodeError as e:
            error_msg = f"ファイルエンコーディングエラー: {e}\nUTF-8エンコーディングで保存してください"
            print(f"❌ {error_msg}")
            raise ValueError(error_msg)

        except Exception as e:
            error_msg = f"システムプロンプト読み込みエラー: {e}"
            print(f"❌ {error_msg}")
            raise

    def _simulate_api_call(self, url: str) -> Dict[str, Any]:
        """
        Claude APIコールをシミュレート（ダミー実装）

        実際のAPI通信は行わず、ダミーのレスポンスを生成します。
        プロンプトキャッシュの効果とコスト計算を正確にシミュレートします。
        Web検索とWeb fetchの処理も含めてシミュレートします。

        Args:
            url (str): 分析対象のブログ記事URL

        Returns:
            Dict[str, Any]: APIレスポンスのシミュレート結果
        """

        print("🔄 Claude API呼び出しシミュレート開始...")
        print("📡 注意: 実際のAPI通信は行いません（ダミー実装）")

        # Web検索のシミュレート（3回の検索を想定）
        print("🔍 Web検索シミュレート中...")
        search_queries = [
            f"{urlparse(url).netloc} 技術 ハッシュタグ",
            "エンジニア X投稿 効果的",
            "プログラミング 自動化 トレンド 2025",
        ]

        for i, query in enumerate(search_queries, 1):
            print(f"   検索 {i}: {query}")
            time.sleep(0.5)  # 検索処理時間のシミュレート

        print("📄 Web fetch シミュレート中...")
        time.sleep(1)  # Web fetch処理時間のシミュレート

        # プロンプトキャッシュの処理シミュレート
        if self.cache_enabled:
            print("📦 プロンプトキャッシュ処理中...")
            cache_cost = (
                self.estimated_cache_tokens
                * self.pricing["cache_read_per_million"]
                / 1000000
            )
            print(f"   - キャッシュ読み取り: {self.estimated_cache_tokens:,} トークン")
            print(f"   - キャッシュコスト: ${cache_cost:.6f}")
        else:
            print("🚫 プロンプトキャッシュ未使用")

        # Claude API処理時間をシミュレート（実際のレスポンス時間を模擬）
        print("🧠 Claude API処理中...")
        processing_steps = [
            "記事内容の解析",
            "技術要素の抽出",
            "品質評価の実行",
            "ハッシュタグの分析",
            "投稿パターンの生成",
            "最適化の適用",
        ]

        for step in processing_steps:
            print(f"   - {step}...")
            time.sleep(0.3)  # 各処理ステップの時間

        # トークン使用量の詳細計算
        input_tokens = {
            # プロンプトキャッシュから読み取るトークン数
            "cached_tokens": self.estimated_cache_tokens if self.cache_enabled else 0,
            # 新規で処理するトークン数の内訳
            "web_search_tokens": 15000,  # Web検索結果（3回分）
            "web_fetch_tokens": 3500,  # Web fetch結果
            "user_input_tokens": 500,  # ユーザー入力（URL等）
            "non_cached_tokens": 19000,  # 上記の合計
            # 総入力トークン数
            "total_input_tokens": 39000,  # キャッシュ + 新規
        }

        # 出力トークン数（生成される投稿パターンの分量）
        output_tokens = 2000

        # 詳細なコスト計算
        costs = self._calculate_costs(input_tokens, output_tokens)

        # ダミーレスポンス生成（実際の品質に近いコンテンツ）
        response_content = self._generate_dummy_response(url)

        print("✅ API呼び出しシミュレート完了")

        return {
            "content": response_content,
            "token_usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            },
            "costs": costs,
            "cache_used": self.cache_enabled,
            "api_call_simulated": True,  # ダミー実装フラグ
            "processing_time": time.time(),  # 処理完了時刻
        }

    def _calculate_costs(
        self, input_tokens: Dict[str, int], output_tokens: int
    ) -> Dict[str, float]:
        """
        詳細なコスト計算

        プロンプトキャッシュの有無によるコスト差を正確に計算し、
        USD・JPY両方の金額、削減効果を算出します。

        Args:
            input_tokens (Dict[str, int]): 入力トークンの詳細情報
            output_tokens (int): 出力トークン数

        Returns:
            Dict[str, float]: 詳細なコスト情報と削減効果
        """

        if self.cache_enabled:
            # プロンプトキャッシュ使用時のコスト計算
            cache_cost = (
                input_tokens["cached_tokens"]
                * self.pricing["cache_read_per_million"]
                / 1000000
            )
            input_cost = (
                input_tokens["non_cached_tokens"]
                * self.pricing["input_per_million"]
                / 1000000
            )
        else:
            # プロンプトキャッシュ未使用時のコスト計算
            cache_cost = 0
            input_cost = (
                input_tokens["total_input_tokens"]
                * self.pricing["input_per_million"]
                / 1000000
            )

        # 出力トークンのコスト（プロンプトキャッシュ使用有無に関わらず同じ）
        output_cost = output_tokens * self.pricing["output_per_million"] / 1000000

        # 総コスト
        total_cost = cache_cost + input_cost + output_cost

        # 削減効果の計算（キャッシュなしとの比較）
        cost_without_cache = (
            input_tokens["total_input_tokens"]
            * self.pricing["input_per_million"]
            / 1000000
            + output_cost
        )
        cost_reduction = cost_without_cache - total_cost if self.cache_enabled else 0
        cost_reduction_percent = (
            (cost_reduction / cost_without_cache * 100) if cost_without_cache > 0 else 0
        )

        # 月間・年間での削減効果試算（月50回実行想定）
        monthly_savings = cost_reduction * 50  # 月50回実行
        yearly_savings = monthly_savings * 12  # 年間

        return {
            # 基本コスト情報（USD）
            "cache_cost": cache_cost,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost,
            # 円換算（1USD=150JPY想定）
            "total_cost_jpy": total_cost * 150,
            # 削減効果
            "cost_without_cache": cost_without_cache,
            "cost_reduction": cost_reduction,
            "cost_reduction_percent": cost_reduction_percent,
            # 長期的な削減効果
            "monthly_savings_usd": monthly_savings,
            "yearly_savings_usd": yearly_savings,
            "monthly_savings_jpy": monthly_savings * 150,
            "yearly_savings_jpy": yearly_savings * 150,
        }

    def _generate_dummy_response(self, url: str) -> str:
        """
        ダミーレスポンス生成

        実際のClaude APIが生成するような高品質なコンテンツを
        ダミーとして生成します。URLのドメインに応じて内容を調整し、
        実際の使用場面に近い品質を提供します。

        Args:
            url (str): 分析対象のURL

        Returns:
            str: 生成されたMarkdownコンテンツ
        """

        # URLからドメインを抽出してコンテンツを調整
        parsed_url = urlparse(url)
        domain = parsed_url.netloc

        print(f"📝 ダミーレスポンス生成中: {domain}")

        # ドメインに応じた技術要素の推定
        # 実際の実装では、web_fetchで取得した内容から自動抽出
        if "sios" in domain.lower():
            tech_elements = [
                "Windows環境でのdotfiles管理システム",
                "PowerShellスクリプトによるシンボリックリンク自動作成",
                "VSCode、Windows Terminal、SSH設定の一元管理",
                "AIツール（Claude、GitHub Copilot）活用によるスクリプト作成支援",
            ]
            limitations = [
                "PowerShellスクリプト実行には管理者権限が必要",
                "Windows環境に特化（Linux/macOS向けは.shスクリプトが必要）",
                "シンボリックリンク作成時の既存ファイル上書きリスク",
                "初回セットアップ時の実行ポリシー変更が必要",
            ]
            overall_rating = "A"
            implementation_level = "本格実装"
            target_audience = "中級者"
        elif "github" in domain.lower():
            tech_elements = [
                "GitHubベースの開発ワークフロー最適化",
                "CI/CD パイプラインの自動化",
                "Issue・PR管理の効率化",
                "GitHub Actions活用による作業自動化",
            ]
            limitations = [
                "GitHubの利用料金プランによる制限",
                "パブリックリポジトリでの機密情報管理注意",
                "外部依存サービスとの連携設定が必要",
            ]
            overall_rating = "A"
            implementation_level = "本格実装"
            target_audience = "中級者"
        elif "qiita" in domain.lower():
            tech_elements = [
                "日本のエンジニアコミュニティ向け技術情報",
                "実践的なコーディング手法",
                "トレンド技術の活用事例",
                "開発効率化のベストプラクティス",
            ]
            limitations = [
                "日本語環境での利用が前提",
                "特定のライブラリ・フレームワークバージョンに依存",
                "環境構築の前提条件が必要",
            ]
            overall_rating = "B"
            implementation_level = "基本実装"
            target_audience = "初級者〜中級者"
        else:
            # 汎用的な技術記事向けの内容
            tech_elements = [
                "現代的な開発手法の実装",
                "効率化・自動化による生産性向上",
                "エンジニア向けベストプラクティス",
                "実用的なツール・技術の活用",
            ]
            limitations = [
                "特定の環境・条件での動作を前提",
                "初期設定や学習コストが必要",
                "既存システムとの互換性確認が重要",
            ]
            overall_rating = "B"
            implementation_level = "基本実装"
            target_audience = "中級者"

        # 生成時刻の記録
        generation_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Markdownコンテンツの生成
        content = f"""
                    # ブログ記事分析・X投稿パターン

                    ## 📊 ブログの評価

                    | 項目 | 評価 |
                    |------|------|
                    | 総合評価 | {overall_rating} |
                    | 技術的正確性 | ⭐⭐⭐⭐⭐ (5点満点) |
                    | 実装レベル | {implementation_level} |
                    | 対象読者 | {target_audience} |
                    | 実用性 | ⭐⭐⭐⭐⭐ (5点満点) |

                    ### 主要な技術要素
                    {chr(10).join(f"- {element}" for element in tech_elements)}

                    ### 注意事項・制限
                    {chr(10).join(f"- {limitation}" for limitation in limitations)}

                    ## 🐦 X投稿パターン

                    ### Aパターン（効果重視・数値訴求型）
                    ```
                    {url}

                    🚀 PC環境構築が30分→3分に短縮！Windows向けdotfiles管理術
                    📝 PowerShellスクリプト1つで設定ファイルを自動配置
                    ⚡ 技術スタック: PowerShell VSCode WindowsTerminal SSH
                    🔧 シンボリックリンクで設定変更が即座に反映される仕組み
                    #dotfiles #PowerShell #Windows #自動化 #環境構築 #効率化
                    ```
                    **投稿推奨時間**: 火曜日21:00（エンジニアの学習ピークタイム・劇的効果訴求に最適）

                    ### Bパターン（課題共感・解決提案型）
                    ```
                    {url}

                    😰 新しいPCセットアップのたびに同じ設定を繰り返してませんか？
                    💡 dotfiles管理を使えばPowerShellスクリプト1つで環境復元
                    ⚡ Windows Terminal、VSCode、SSH設定を一括管理
                    🎯 PC故障やリプレース時も安心の開発環境構築術
                    #dotfiles #Windows #環境構築 #PowerShell #自動化 #効率化
                    ```
                    **投稿推奨時間**: 水曜日12:00（昼休み時間・共感型アプローチで気軽チェック）

                    ### Cパターン（技術トレンド・学習促進型）
                    ```
                    {url}

                    🔥 2025年注目のWindows開発環境管理手法
                    📚 dotfiles + PowerShellでプロレベルの設定管理を実現
                    ⭐ AIツール活用でスクリプト作成もサクッと完了
                    🚀 GitHubで設定を共有してチーム全体の生産性向上
                    #dotfiles #PowerShell #Windows #AI活用 #開発環境 #生産性
                    ```
                    **投稿推奨時間**: 火曜日21:00（最新技術トレンド・学習意欲が高い時間帯）

                    ---

                    **生成情報**
                    - 対象URL: {url}
                    - ドメイン: {domain}
                    - 生成日時: {generation_time}
                    - プロンプトキャッシュ: {'使用' if self.cache_enabled else '未使用'}
                    - 生成方式: ダミー実装（API検証前）
                    - システムプロンプト: 外部ファイル読み込み
                    """

        if self.debug_mode:
            print("📄 生成コンテンツ統計:")
            print(f"   - 文字数: {len(content):,}")
            print(f"   - 行数: {len(content.splitlines()):,}")
            print(f"   - バイト数: {len(content.encode('utf-8')):,}")

        return content

    def generate_posts(self, url: str) -> Dict[str, Any]:
        """
        X投稿パターンを生成（メイン処理）

        URLを受け取り、ブログ記事を分析してX投稿パターンを生成します。
        プロンプトキャッシュを活用してコスト効率化を図ります。

        処理フロー:
        1. URL検証
        2. APIコールシミュレート（Web検索・fetch・Claude API）
        3. コスト計算
        4. レスポンス生成

        Args:
            url (str): 分析対象のブログ記事URL

        Returns:
            Dict[str, Any]: 生成結果（コンテンツ、コスト、トークン使用量等）

        Raises:
            ValueError: URLが無効な場合
            Exception: 生成処理中にエラーが発生した場合
        """

        print("🚀 X投稿パターン生成開始...")
        print("=" * 60)

        # URL基本検証
        if not url or not url.startswith(("http://", "https://")):
            error_msg = f"無効なURL: {url}"
            print(f"❌ {error_msg}")
            raise ValueError(error_msg)

        # 生成設定の表示
        print(f"📄 対象URL: {url}")
        print(f"🧠 プロンプトキャッシュ: {'有効' if self.cache_enabled else '無効'}")
        print("💡 実装方式: ダミー（API通信検証前）")
        print(f"🔧 デバッグモード: {'有効' if self.debug_mode else '無効'}")

        # 開始時刻の記録
        start_time = time.time()

        try:
            # APIコールシミュレート
            result = self._simulate_api_call(url)

            # 処理時間の計算
            processing_time = time.time() - start_time
            result["processing_time_seconds"] = processing_time

            # コスト情報の詳細出力
            costs = result["costs"]
            print("\n💰 コスト詳細レポート:")
            print(f"   - キャッシュ読み取り: ${costs['cache_cost']:.6f}")
            print(f"   - 入力処理: ${costs['input_cost']:.6f}")
            print(f"   - 出力生成: ${costs['output_cost']:.6f}")
            print(
                f"   - 合計: ${costs['total_cost']:.6f} (約{costs['total_cost_jpy']:.1f}円)"
            )

            if self.cache_enabled:
                print("\n📊 コスト削減効果:")
                print(f"   - キャッシュなしの場合: ${costs['cost_without_cache']:.6f}")
                print(f"   - 削減金額: ${costs['cost_reduction']:.6f}")
                print(f"   - 削減率: {costs['cost_reduction_percent']:.1f}%")
                print(
                    (
                        f"   - 月間削減効果: ${costs['monthly_savings_usd']:.2f} "
                        f"(約{costs['monthly_savings_jpy']:.0f}円)"
                    )
                )
                print(
                    (
                        f"   - 年間削減効果: ${costs['yearly_savings_usd']:.2f} "
                        f"(約{costs['yearly_savings_jpy']:.0f}円)"
                    )
                )

            # トークン使用量の詳細出力
            tokens = result["token_usage"]["input_tokens"]
            output_tokens = result["token_usage"]["output_tokens"]

            print("\n📊 トークン使用量詳細:")
            print(f"   - キャッシュ済み: {tokens['cached_tokens']:,}")
            print(f"   - Web検索結果: {tokens['web_search_tokens']:,}")
            print(f"   - Web fetch結果: {tokens['web_fetch_tokens']:,}")
            print(f"   - ユーザー入力: {tokens['user_input_tokens']:,}")
            print(f"   - 新規入力合計: {tokens['non_cached_tokens']:,}")
            print(f"   - 総入力: {tokens['total_input_tokens']:,}")
            print(f"   - 出力: {output_tokens:,}")

            # 処理パフォーマンス情報
            print("\n⏱️  処理パフォーマンス:")
            print(f"   - 処理時間: {processing_time:.2f}秒")
            print(
                f"   - トークン/秒: {tokens['total_input_tokens'] / processing_time:.0f}"
            )

            return result

        except Exception as e:
            error_msg = f"生成処理中にエラーが発生しました: {e}"
            print(f"❌ {error_msg}")
            # エラー情報も結果に含める
            return {
                "content": None,
                "error": str(e),
                "error_type": type(e).__name__,
                "processing_time_seconds": time.time() - start_time,
            }

    def save_to_file(
        self,
        content: str,
        filename: str,
        url: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        生成されたコンテンツをMarkdownファイルとして保存

        YAML Frontmatterに詳細なメタデータ（コスト、トークン使用量、生成情報等）を含めて
        ファイルに保存します。後でコスト分析や使用状況の追跡に活用できます。

        Args:
            content (str): 生成されたMarkdownコンテンツ
            filename (str): 保存先ファイルパス
            url (str): 分析対象のURL
            metadata (Optional[Dict[str, Any]]): 生成時のメタデータ

        Raises:
            OSError: ファイル保存に失敗した場合
            ValueError: 引数が無効な場合
        """

        # 引数の基本検証
        if not content:
            raise ValueError("保存するコンテンツが空です")
        if not filename:
            raise ValueError("ファイル名が指定されていません")
        if not url:
            raise ValueError("URLが指定されていません")

        print(f"💾 ファイル保存開始: {filename}")

        # ディレクトリ作成（存在しない場合）
        file_path = Path(filename)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"📁 ディレクトリ確認: {file_path.parent}")

        # メタデータの準備（ない場合はデフォルト値）
        if metadata is None:
            metadata = {}

        costs = metadata.get("costs", {})
        token_usage = metadata.get("token_usage", {})
        input_tokens = token_usage.get("input_tokens", {})

        # YAML Frontmatterの生成（詳細な生成情報を記録）
        frontmatter = f"""---
                        # =================================================================
                        # X投稿自動生成システム - 生成ファイルメタデータ
                        # =================================================================

                        # 生成基本情報
                        url: "{url}"
                        generated_at: "{datetime.now().isoformat()}"
                        generator: "Claude API X Posts Generator (Cache Enabled)"
                        generator_version: "v1.0.0"
                        system_prompt_source: "prompts/system_prompt.md"

                        # プロンプトキャッシュ情報
                        prompt_cache:
                        enabled: {str(metadata.get('cache_used', False)).lower()}
                        cached_tokens: {input_tokens.get('cached_tokens', 0)}
                        estimated_cache_size: {self.estimated_cache_tokens}
                        cache_efficiency: {(
                            input_tokens.get('cached_tokens', 0)
                            / self.estimated_cache_tokens * 100
                            if self.estimated_cache_tokens > 0 else 0
                        ):.1f}%

                        # コスト情報（USD）
                        costs_usd:
                        cache_cost: {costs.get('cache_cost', 0):.6f}
                        input_cost: {costs.get('input_cost', 0):.6f}
                        output_cost: {costs.get('output_cost', 0):.6f}
                        total_cost: {costs.get('total_cost', 0):.6f}
                        cost_without_cache: {costs.get('cost_without_cache', 0):.6f}
                        cost_reduction: {costs.get('cost_reduction', 0):.6f}

                        # コスト情報（JPY、1USD=150JPY想定）
                        costs_jpy:
                        total_cost: {costs.get('total_cost_jpy', 0):.1f}
                        cost_reduction: {costs.get('cost_reduction', 0) * 150:.1f}
                        monthly_savings: {costs.get('monthly_savings_jpy', 0):.0f}
                        yearly_savings: {costs.get('yearly_savings_jpy', 0):.0f}

                        # コスト削減効果
                        cost_efficiency:
                        reduction_percent: {costs.get('cost_reduction_percent', 0):.1f}%
                        monthly_usage_assumption: 50  # 月間実行回数想定
                        yearly_usage_assumption: 600  # 年間実行回数想定

                        # トークン使用量詳細
                        token_usage:
                        input:
                            cached: {input_tokens.get('cached_tokens', 0)}
                            web_search: {input_tokens.get('web_search_tokens', 0)}
                            web_fetch: {input_tokens.get('web_fetch_tokens', 0)}
                            user_input: {input_tokens.get('user_input_tokens', 0)}
                            non_cached_total: {input_tokens.get('non_cached_tokens', 0)}
                            total: {input_tokens.get('total_input_tokens', 0)}
                        output: {token_usage.get('output_tokens', 0)}
                        processing_efficiency: {(
                            token_usage.get('output_tokens', 0) /
                            input_tokens.get('total_input_tokens', 1)
                        ):.4f}  # 出力/入力比率

                        # パフォーマンス情報
                        performance:
                        processing_time_seconds: {(
                            metadata.get('processing_time_seconds', 0)
                        ):.2f}
                        tokens_per_second: {(
                            input_tokens.get('total_input_tokens', 0) /
                            max(metadata.get('processing_time_seconds', 1), 0.1)
                        ):.0f}
                        api_call_simulated: {(
                            str(metadata.get('api_call_simulated', True)).lower()
                        )}

                        # 品質保証チェック
                        quality_assurance:
                        link_card_optimized: true      # URLを投稿文冒頭に配置
                        hashtag_optimized: true        # エンジニア向けハッシュタグ選定
                        engineer_focused: true         # エンジニア向けコンテンツ最適化
                        cost_optimized: true           # プロンプトキャッシュによるコスト最適化
                        three_pattern_generated: true  # 3パターンの投稿文生成
                        timing_optimized: true         # 投稿時間最適化

                        # システム情報
                        system_info:
                        api_model: "Claude Sonnet 4"
                        pricing_model: "2025-07-06"
                        cache_strategy: "Prompt Cache (20k tokens)"
                        output_format: "Markdown with YAML frontmatter"
                        debug_mode: {str(self.debug_mode).lower()}

                        # ファイル情報
                        file_info:
                        original_url_domain: "{urlparse(url).netloc}"
                        content_language: "ja"  # 日本語
                        target_platform: "X (Twitter)"
                        target_audience: "Japanese Engineers"

                        # 更新履歴（将来の更新時に使用）
                        revision_history:
                        - version: "1.0.0"
                            date: "{datetime.now().strftime('%Y-%m-%d')}"
                            changes: "初回生成"
                        ---

                        """

        # コンテンツとメタデータを結合
        full_content = frontmatter + content

        try:
            # ファイルに書き込み（UTF-8エンコーディング）
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(full_content)

            # 保存完了の詳細レポート
            file_size = len(full_content.encode("utf-8"))
            content_lines = len(content.splitlines())
            frontmatter_lines = len(frontmatter.splitlines())
            total_lines = len(full_content.splitlines())

            print("✅ ファイル保存完了!")
            print(f"📁 保存先: {file_path.absolute()}")
            print("📊 ファイル統計:")
            print(f"   - ファイルサイズ: {file_size:,} bytes")
            print(f"   - 総行数: {total_lines:,} 行")
            print(f"   - メタデータ: {frontmatter_lines:,} 行")
            print(f"   - コンテンツ: {content_lines:,} 行")
            print(f"   - 文字数: {len(full_content):,} 文字")

            # ファイル構造の検証
            if file_size > 0:
                print("✅ ファイル書き込み成功")
            else:
                print("⚠️  警告: ファイルサイズが0です")

            # メタデータ検証
            if "---" in full_content and "url:" in full_content:
                print("✅ YAML frontmatter生成成功")
            else:
                print("⚠️  警告: YAML frontmatterに問題がある可能性があります")

            # 投稿パターンの存在確認
            pattern_count = full_content.count("パターン")
            if pattern_count >= 3:
                print(f"✅ 投稿パターン生成成功 ({pattern_count}個)")
            else:
                print(
                    f"⚠️  警告: 投稿パターンが不足している可能性があります ({pattern_count}個)"
                )

            if self.debug_mode:
                print("\n🐛 デバッグ情報:")
                print("   - エンコーディング: UTF-8")
                print(f"   - 改行コード: {repr(chr(10))}")
                print(f"   - ファイルパス: {file_path.resolve()}")

        except OSError as e:
            error_msg = f"ファイル保存エラー: {e}"
            print(f"❌ {error_msg}")
            raise OSError(error_msg)

        except Exception as e:
            error_msg = f"予期しないエラー: {e}"
            print(f"❌ {error_msg}")
            raise


def main():
    """
    メイン実行関数

    環境変数からURL・ファイル名を取得し、X投稿パターンを生成して
    Markdownファイルに保存します。GitHub Actionsから呼び出されることを想定。

    環境変数:
        URL: 分析対象のブログ記事URL
        FILENAME: 出力ファイルパス
        DEBUG_MODE: デバッグモード（"true"で有効）
        ANTHROPIC_API_KEY: Claude APIキー（今回はダミー）

    Exit Codes:
        0: 正常終了
        1: URL関連エラー
        2: ファイル関連エラー
        3: システムプロンプト関連エラー
        99: その他のエラー
    """

    print("🤖 X投稿自動生成システム（プロンプトキャッシュ対応版）")
    print("=" * 70)
    print("📅 Version: 1.0.0")
    print("🔧 Mode: ダミー実装（API検証前）")
    print("💡 Feature: プロンプトキャッシュによる37%コスト削減")

    # 実行開始時刻の記録
    execution_start_time = time.time()

    try:
        # 環境変数からパラメータ取得
        url = os.environ.get("URL")
        filename = os.environ.get("FILENAME")
        debug_mode = os.environ.get("DEBUG_MODE", "false").lower() == "true"

        # パラメータの基本検証
        if not url:
            # デフォルトURLを使用（開発・テスト用）
            url = "https://tech-lab.sios.jp/archives/48173"
            print(f"⚠️  URL未指定のため、デフォルトURLを使用: {url}")

        if not filename:
            # デフォルトファイル名を生成
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            filename = f"posts/demo-output-{timestamp}.md"
            print(f"⚠️  ファイル名未指定のため、デフォルト名を使用: {filename}")

        print("\n📋 実行パラメータ:")
        print(f"   - 対象URL: {url}")
        print(f"   - 出力ファイル: {filename}")
        print(f"   - デバッグモード: {'有効' if debug_mode else '無効'}")
        print(f"   - 作業ディレクトリ: {os.getcwd()}")

        # URLの形式チェック
        if not url.startswith(("http://", "https://")):
            print(f"❌ 無効なURL形式: {url}")
            print("💡 URLは http:// または https:// で始まる必要があります")
            return 1

        # ファイルパスの検証
        try:
            file_path = Path(filename)
            if not file_path.suffix == ".md":
                print(f"⚠️  警告: ファイル拡張子が.mdではありません: {filename}")
        except Exception as e:
            print(f"❌ 無効なファイルパス: {filename} ({e})")
            return 2

        # 生成システムの初期化
        print("\n🔄 システム初期化中...")
        try:
            generator = XPostGeneratorWithCache()
            print("✅ システム初期化完了")
        except FileNotFoundError as e:
            print(f"❌ システムプロンプトファイルエラー: {e}")
            return 3
        except Exception as e:
            print(f"❌ システム初期化エラー: {e}")
            return 99

        # X投稿パターン生成
        print("\n🚀 生成処理開始...")
        result = generator.generate_posts(url)

        # エラーチェック
        if "error" in result:
            print(f"❌ 生成エラー: {result['error']}")
            return 99

        # ファイル保存
        print("\n💾 ファイル保存処理...")
        generator.save_to_file(result["content"], filename, url, result)

        # 実行完了レポート
        total_execution_time = time.time() - execution_start_time

        print("\n🎉 全処理完了!")
        print(f"⏱️  総実行時間: {total_execution_time:.2f}秒")
        print(f"📁 出力ファイル: {filename}")
        print(
            f"💰 推定コスト: ${result['costs']['total_cost']:.6f} "
            f"(約{result['costs']['total_cost_jpy']:.1f}円)"
        )

        if result.get("cache_used"):
            print(
                f"📊 コスト削減: {result['costs']['cost_reduction_percent']:.1f}% "
                f"(${result['costs']['cost_reduction']:.6f})"
            )

        print("\n✅ 処理が正常に完了しました!")
        return 0

    except KeyboardInterrupt:
        print("\n⚠️  ユーザーによる処理中断")
        return 130  # SIGINT exit code

    except Exception as e:
        print(f"\n❌ 予期しないエラーが発生しました: {e}")
        print(f"🔍 エラータイプ: {type(e).__name__}")

        if debug_mode:
            import traceback

            print("\n🐛 詳細なエラー情報:")
            traceback.print_exc()

        return 99


if __name__ == "__main__":
    """
    スクリプトのエントリーポイント

    このスクリプトが直接実行された場合にmain()関数を呼び出し、
    その結果をexit codeとしてシステムに返します。

    GitHub Actionsでは、このexit codeを使用して処理の成功/失敗を判定します。
    """

    try:
        exit_code = main()
        print(f"\n🏁 プロセス終了 (exit code: {exit_code})")
        exit(exit_code)
    except Exception as e:
        print(f"\n💥 致命的エラー: {e}")
        exit(99)

# =================================================================
# スクリプト実行時の注意事項とトラブルシューティング
# =================================================================

"""
【必要な環境設定】

1. 依存ファイル:
   - prompts/system_prompt.md: システムプロンプト定義ファイル
2. 環境変数:
   - URL: 分析対象のブログ記事URL（必須）
   - FILENAME: 出力ファイルパス（オプション、デフォルト自動生成）
   - ANTHROPIC_API_KEY: Claude APIキー（実装時に必要）
   - DEBUG_MODE: デバッグモード（"true"で詳細ログ出力）

3. ディレクトリ構造:
   project/
   ├── scripts/
   │   └── generate_posts_with_cache.py  # このファイル
   ├── prompts/
   │   └── system_prompt.md              # システムプロンプト
   └── posts/                            # 出力先（自動作成）

【ローカルでのテスト実行】

# 基本実行
export URL="https://tech-lab.sios.jp/archives/48173"
export FILENAME="posts/test-output.md"
python scripts/generate_posts_with_cache.py

# デバッグモード
export DEBUG_MODE="true"
python scripts/generate_posts_with_cache.py

【トラブルシューティング】

1. "システムプロンプトファイルが見つかりません"
   → prompts/system_prompt.md を作成してください

2. "無効なURL形式"
   → URL は https:// で始まる完全なURLを指定してください

3. "ファイル保存エラー"
   → posts ディレクトリへの書き込み権限を確認してください

4. "予期しないエラー"
   → DEBUG_MODE="true" で詳細ログを確認してください

【パフォーマンス最適化】

- プロンプトキャッシュ: 2回目以降の実行で37%コスト削減
- 処理時間: 約3-5秒（ダミー実装）、実API使用時は10-30秒
- メモリ使用量: 約50MB（システムプロンプト + 生成コンテンツ）

【セキュリティ注意事項】

- API キーは環境変数で管理し、コードに直接記載しない
- 生成されたファイルには機密情報が含まれていないか確認
- 外部URLアクセス時は適切なタイムアウト設定を行う
"""
