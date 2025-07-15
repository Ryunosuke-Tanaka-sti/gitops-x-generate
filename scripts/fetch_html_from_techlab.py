import requests
from bs4 import BeautifulSoup
import os
import re


def fetch_and_parse_html(url):
    """
    URLからHTMLを取得してパースする関数

    Args:
        url (str): 取得するURL

    Returns:
        BeautifulSoup: パースされたHTMLオブジェクト
    """
    try:
        # HTTPリクエストを送信
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # HTTPエラーがあれば例外を発生

        # HTMLをパース
        soup = BeautifulSoup(response.content, "html.parser")

        return soup

    except requests.exceptions.RequestException as e:
        print(f"URLの取得でエラーが発生しました: {e}")
        return None
    except Exception as e:
        print(f"予期しないエラーが発生しました: {e}")
        return None


def estimate_claude_tokens(text):
    """
    Claude用のトークン数概算関数

    Claude（日本語）の場合：
    - ひらがな・カタカナ: 約1.5文字/トークン
    - 漢字: 約1文字/トークン
    - 英数字: 約4文字/トークン
    - HTML: 約3文字/トークン

    Args:
        text (str): 計算対象のテキスト

    Returns:
        int: 推定トークン数
    """
    if not text:
        return 0

    # 文字種別にカウント
    hiragana_katakana = len(
        [c for c in text if "\u3040" <= c <= "\u309f" or "\u30a0" <= c <= "\u30ff"]
    )
    kanji = len([c for c in text if "\u4e00" <= c <= "\u9faf"])
    ascii_chars = len([c for c in text if ord(c) < 128])
    other_chars = len(text) - hiragana_katakana - kanji - ascii_chars

    # トークン数を推定
    estimated_tokens = (
        hiragana_katakana / 1.5
        + kanji / 1.0
        + ascii_chars / 4.0
        + other_chars / 2.0  # その他の文字
    )
    return int(estimated_tokens)


def extract_and_compress_content_bs4(soup, target_selector="section.entry-content"):
    """
    BeautifulSoupを使用したバージョン（より柔軟な抽出が可能）

    Args:
        soup (BeautifulSoup): パースされたHTMLオブジェクト
        target_selector (str): 抽出対象のCSSセレクタ

    Returns:
        str: 圧縮されたコンテンツ
    """

    try:
        title = soup.find("title")

        # CSSセレクタで要素を検索
        target_elements = soup.select(target_selector)

        if not target_elements:
            print(
                f"指定されたセレクタ '{target_selector}' に該当する要素が見つかりませんでした"
            )
            return ""

        # 最初の要素を使用
        target_element = target_elements[0]

        # 圧縮前のトークン数を計算（元のページ全体）
        original_full_tokens = estimate_claude_tokens(str(soup))
        # 抽出対象要素のトークン数を計算（抽出後）
        extracted_tokens = estimate_claude_tokens(str(target_element))

        # 不要な要素を削除（scriptタグ、styleタグなど）
        for tag in target_element(["script", "style", "noscript"]):
            tag.decompose()

        # imgタグのalt属性を処理（alt属性をテキストとして残す）
        img_tags = target_element.find_all("img", alt=True)
        for img in img_tags:
            alt_text = img.get("alt", "")
            if alt_text:
                # imgタグの後にalt属性のテキストを追加
                img.insert_after(f" {alt_text} ")
            # src属性以外の属性を削除してHTMLを軽量化
            img.attrs = {}

        # 全ての要素から不要な属性を削除（クラス、ID、スタイルなど）
        for tag in target_element.find_all(True):
            # 基本的なタグのみ保持
            if tag.name in ["a"]:
                # リンクのhref属性のみ保持
                href = tag.get("href")
                tag.attrs.clear()
                if href:
                    tag["href"] = href
            else:
                tag.attrs.clear()

        # HTMLを文字列として取得（圧縮前の状態）
        original_html_str = str(target_element)

        # 圧縮処理（HTML構造と改行は維持、余分な空白のみ削除）
        compressed_content = original_html_str
        compressed_content = re.sub(
            r">\s+<", "><", compressed_content
        )  # タグ間の空白削除

        # 最終的な圧縮後のトークン数を計算
        final_compressed_tokens = estimate_claude_tokens(compressed_content)

        # 詳細情報を表示
        print(f"元ページ全体のトークン数: {original_full_tokens:,}")
        print(f"抽出後のトークン数: {extracted_tokens:,}")
        print(f"最終圧縮後のトークン数: {final_compressed_tokens:,}")
        print(f"抽出による削減: {original_full_tokens - extracted_tokens:,}")
        print(f"圧縮による削減: {extracted_tokens - final_compressed_tokens:,}")
        print(f"総削減トークン数: {original_full_tokens - final_compressed_tokens:,}")

        # 全体的な圧縮率の計算（元ページ全体 → 最終圧縮後）
        if original_full_tokens > 0:
            total_compression_ratio = (
                (original_full_tokens - final_compressed_tokens)
                / original_full_tokens
                * 100
            )
        else:
            total_compression_ratio = 0

        # 抽出のみの効果
        if original_full_tokens > 0:
            extraction_ratio = (
                (original_full_tokens - extracted_tokens) / original_full_tokens * 100
            )
        else:
            extraction_ratio = 0

        # 圧縮のみの効果
        if extracted_tokens > 0:
            compression_only_ratio = (
                (extracted_tokens - final_compressed_tokens) / extracted_tokens * 100
            )
        else:
            compression_only_ratio = 0

        print(f"抽出による削減率: {extraction_ratio:.2f}%")
        print(f"圧縮による削減率: {compression_only_ratio:.2f}%")
        print(f"総合圧縮率: {total_compression_ratio:.2f}%")

        # タイトルと結合して返答
        result = f"<h1>{title.get_text(strip=True)}</h1>\n\n{compressed_content}"

        return result

    except Exception as e:
        print(f"BeautifulSoupでの処理中にエラーが発生しました: {e}")
        return ""


def main():
    """
    メイン関数
    """
    url = os.environ.get("URL")
    if not url:
        # デフォルトURLを使用（開発・テスト用）
        url = "https://tech-lab.sios.jp/archives/48173"
        print(f"⚠️  URL未指定のため、デフォルトURLを使用: {url}")

    # URLの簡単な検証
    if not url.startswith("https://tech-lab.sios.jp/archives"):
        raise ValueError(
            "URLは 'https://tech-lab.sios.jp/archives' で始まる必要があります"
        )

    # html_cacheディレクトリが存在しない場合は作成
    cache_dir = "html_cache"
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
        print(f"{cache_dir}ディレクトリを作成しました。")

    # HTMLファイルパスの生成（URL -> ファイル名変換）
    # 例: https://tech-lab.sios.jp/archives/48173 -> tech-lab-sios-jp-archives-48173.html
    domain_path = (
        url.replace("https://", "")
        .replace("http://", "")
        .replace("/", "-")
        .replace(".", "-")
    )
    html_file_path = f"{cache_dir}/{domain_path}.html"

    print(f"📁 HTMLファイル保存先: {html_file_path}")

    # htmlファイルが既に存在する場合は後続の処理をスキップ
    if os.path.exists(html_file_path):
        print(f"✅ {html_file_path} が既に存在するため、後続の処理をスキップします。")
        print(f"📊 ファイルサイズ: {os.path.getsize(html_file_path)} bytes")
        return

    # HTMLを取得してパース
    print("🔄 HTML取得・パース開始...")
    soup = fetch_and_parse_html(url)

    if soup is None:
        raise RuntimeError("HTMLの取得に失敗しました")

    # 基本情報を抽出して表示
    title = soup.find("title")
    if title:
        print(f"📄 ページタイトル: {title.get_text().strip()}")

    # コンテンツを抽出・圧縮
    print("🔧 コンテンツ抽出・圧縮開始...")
    result = extract_and_compress_content_bs4(soup)

    if not result:
        raise RuntimeError("コンテンツの抽出に失敗しました")

    # HTMLファイルに保存
    print(f"💾 HTMLファイル保存中: {html_file_path}")
    try:
        with open(html_file_path, "w", encoding="utf-8") as f:
            f.write(result)

        # 保存確認
        if os.path.exists(html_file_path):
            file_size = os.path.getsize(html_file_path)
            print(f"✅ HTMLファイルを保存しました: {html_file_path}")
            print(f"📊 ファイルサイズ: {file_size} bytes")
        else:
            raise RuntimeError("HTMLファイルの保存に失敗しました")

    except Exception as e:
        print(f"❌ HTMLファイル保存エラー: {e}")
        raise


if __name__ == "__main__":
    main()
