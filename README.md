やることリスト

1.vectra の初期設定
　・Scalp.ini ファイルの IP アドレス更新
　・撮影部位の指定

2.撮影内容の pdf ファイルの作成
　・新規のフォルダを検出し、tricho*{i}.json ファイルを取得
　・tricho*{i}.json を用いてレポートを作成
　・作成されたレポートを表示する

上記の解決にはアプリケーションを作成するのが良いのでは？
　・vectra の再起動
　　・ini ファイルの再設定
　　・患者データの作成
　・撮影部位の指定
　・作成されたレポートの表示


使い方

python ./deta_extractor ./sample_data/path ./sample_data/HairReport.pdf
node ./report_template ./sample_data/TempPath