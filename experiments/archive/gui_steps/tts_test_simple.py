#!/usr/bin/env python3
"""
Simple TTS Test without external dependencies
外部依存なしのシンプルTTSテスト
"""

import os
import sys
from pathlib import Path

# Import analysis modules
from api_limiter import APILimiter, APIType, LimitMode, create_test_limiter
from pronunciation_dict import PronunciationDictionary, create_orion_dictionary

def test_api_environment():
    """API環境確認テスト"""
    print("🔍 API環境確認テスト")
    print("=" * 40)
    
    # 環境変数確認
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if api_key:
        masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        print(f"✅ ELEVENLABS_API_KEY: {masked_key}")
    else:
        print("❌ ELEVENLABS_API_KEY: 未設定")
        print("💡 設定方法: export ELEVENLABS_API_KEY=your_api_key")
    
    # 音声ID確認
    voice_ids = {
        "NARRATION": os.getenv("ELEVENLABS_VOICE_ID_NARRATION", "未設定"),
        "DIALOGUE": os.getenv("ELEVENLABS_VOICE_ID_DIALOGUE", "未設定"),
    }
    
    for name, voice_id in voice_ids.items():
        if voice_id != "未設定":
            masked_id = voice_id[:8] + "..." if len(voice_id) > 8 else voice_id
            print(f"✅ {name}: {masked_id}")
        else:
            print(f"⚠️ {name}: {voice_id}")
    
    return api_key is not None

def test_analysis_systems():
    """解析システムテスト"""
    print("\n🧪 解析システムテスト")
    print("=" * 40)
    
    try:
        # API制限システム
        print("📊 API制限システム...")
        limiter = create_test_limiter(LimitMode.DEMO)
        
        test_text = "ニーチェは哲学者です。"
        allowed, reason = limiter.check_limits(APIType.ELEVENLABS_TTS, len(test_text))
        print(f"制限チェック: {'✅ 許可' if allowed else '❌ 拒否'}")
        print(f"理由: {reason}")
        
        # 発音辞書システム
        print("\n📚 発音辞書システム...")
        dictionary = create_orion_dictionary()
        
        matches = dictionary.find_matches_in_text(test_text)
        print(f"辞書マッチ: {len(matches)}語")
        for word, entry in matches:
            print(f"  {word} → {entry.reading}")
        
        # 発音適用テスト
        processed_text = dictionary.apply_pronunciation_to_text(test_text, "reading")
        print(f"原文: {test_text}")
        print(f"読み: {processed_text}")
        
        return True
        
    except Exception as e:
        print(f"❌ 解析システムエラー: {e}")
        return False

def test_orion_sample():
    """オリオンEP1サンプルテスト"""
    print("\n🎯 オリオンEP1サンプルテスト")
    print("=" * 40)
    
    # オリオンEP1からの抜粋
    orion_samples = [
        "転職した同期の投稿を見て、焦りを感じたことはありませんか？",
        "19世紀のドイツ。哲学者フリードリヒ・ニーチェは、現代人の精神状態を鋭く分析しました。",
        "fMRI（機能的磁気共鳴画像法）による脳科学研究が示唆するのは、不確実性に直面した時の私たちの反応パターンです。"
    ]
    
    try:
        # 制限・辞書システム初期化
        limiter = create_test_limiter(LimitMode.DEVELOPMENT)
        dictionary = create_orion_dictionary()
        
        for i, sample in enumerate(orion_samples, 1):
            print(f"\n--- サンプル {i} ---")
            print(f"原文: {sample}")
            
            # 制限チェック
            allowed, reason = limiter.check_limits(APIType.ELEVENLABS_TTS, len(sample))
            print(f"制限: {'✅ 許可' if allowed else '❌ 拒否'} ({reason})")
            
            # 発音辞書適用
            matches = dictionary.find_matches_in_text(sample)
            if matches:
                print(f"専門用語: {', '.join([word for word, _ in matches])}")
                
                processed = dictionary.apply_pronunciation_to_text(sample, "reading")
                print(f"読み: {processed}")
            else:
                print("専門用語: なし")
            
            # 文字数・推定コスト
            char_count = len(sample)
            estimated_cost = char_count * 0.00018
            print(f"文字数: {char_count}, 推定コスト: ${estimated_cost:.4f}")
        
        return True
        
    except Exception as e:
        print(f"❌ サンプルテストエラー: {e}")
        return False

def main():
    """メインテスト実行"""
    print("🎤 TTS実践テスト準備")
    print("=" * 50)
    
    # 各テスト実行
    env_ok = test_api_environment()
    analysis_ok = test_analysis_systems()
    sample_ok = test_orion_sample()
    
    # 結果サマリー
    print("\n📋 テスト結果サマリー")
    print("=" * 50)
    print(f"API環境: {'✅' if env_ok else '❌'}")
    print(f"解析システム: {'✅' if analysis_ok else '❌'}")
    print(f"サンプルテスト: {'✅' if sample_ok else '❌'}")
    
    if env_ok and analysis_ok and sample_ok:
        print("\n🚀 実TTS生成の準備完了！")
        print("次のステップ: GUI統合でのTTS実行")
    else:
        print("\n⚠️ 問題があります。上記エラーを確認してください。")

if __name__ == "__main__":
    main()