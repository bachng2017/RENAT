#!/usr/bin/ruby -Ks
ScriptDescription="MIB Data Pooling Script By masayuki.azuma@gmail.com"
Version="2016.11.02"
#
# 更新履歴等
# 2015/07/07 とりあえず作った
# 2015/07/09 SNMPGet timeout時の例外処理追加
# 2015/08/20 BPS,PPS計算を追加。これに伴いcsvヘッダにdescriptionだけでなくdisp形式も記載するようにした
# 2016/01/18 CPU Loadのように小数点以下の値を持つ場合に小数点以下がto_iで切り捨てされてしまったのでto_fにするgaugefを追加した
# 2016/11/02 小数点の桁数を合わせるため、gaugef2を追加した

require 'rubygems'
require 'optparse'
require 'json'
require 'snmp'

# オプション指定しない場合のデフォルトパラメータ設定
community    = 'public'
mdatafile    = 'mib-Sample.json'
target       = '127.0.0.1'
interval     = 10
snmp_timeout = 1    # SNMP getのタイムアウト時間(秒)

# その他パラメータ
snmp_retry   = 1    # SNMP getタイムアウト時の再試行回数

# コマンドラインオプションの読み込み
opt = OptionParser.new
OPTS = {}
opt.banner="Usage: Pooling.rb [options]"
opt.on("-c [community]"   , desc="# default = #{community}"){|v| OPTS[:c] = v}
opt.on("-m [mib.json]"    , desc="# default = #{mdatafile}"){|v| OPTS[:m] = v}
opt.on("-t [terget_ip]"   , desc="# default = #{target}")   {|v| OPTS[:t] = v}
opt.on("-i [interval]"    , desc="# default = #{interval}") {|v| OPTS[:i] = v}
opt.on("-o [snmp_timeout]", desc="# default = #{snmp_timeout}")  {|v| OPTS[:o] = v}
opt.on("-d"               , desc="# DEBUG ENABLE")          {|v| OPTS[:d] = v}
opt.on_tail("\n#{ScriptDescription}\nVersion: #{Version}")
opt.parse!(ARGV)

if OPTS[:c] then community    = OPTS[:c]      end
if OPTS[:m] then mdatafile    = OPTS[:m]      end
if OPTS[:t] then target       = OPTS[:t]      end
if OPTS[:i] then interval     = OPTS[:i].to_i end
if OPTS[:o] then snmp_timeout = OPTS[:o].to_i end
if OPTS[:d] then $DEBUG       = true          end

# 入力データ補正
if interval < 1 then interval = 1 end

# MIB取得を失敗した際の待ち時間
if interval < (snmp_timeout * (snmp_retry + 1)) then
  interval_rescue = 0
else
  interval_rescue = interval - (snmp_timeout * (snmp_retry + 1))
end

# バッファせずに即時出力。リダイレクト等の際に効いてくる
STDOUT.sync = true
print "##SNMP Pooling:target=\"#{target}\" mdata=\"#{mdatafile}\" community=\"#{community}\" interval=#{interval} snmp_timeout=#{snmp_timeout}\n"

# ポーリング対象MIB情報ファイルを読み込む。JSON使ってみるよ
data = open(mdatafile) do |io|
  JSON.load(io)
end

# MIB情報ファイルからポーリングOID等を読み込みつつCSVヘッダ表示。多次元配列的にするべきではある
arrayOld  = Array.new
arrayOID  = Array.new
arrayDisp = Array.new
print "#time"
data['miblist'].each do |obj|
  print ',',     obj["decription"]
  print ':',     obj["disp"]
  arrayOID.push( obj["oid"])
  arrayDisp.push(obj["disp"])
  arrayOld.push(nil) # initialize
end
puts

# SNMPポーリング実施
SNMP::Manager.open(:host => target, :community => community, :timeout => snmp_timeout, :retries => snmp_retry) do |manager|
  Signal.trap(:INT){ # Ctrl+Cで終了されたときに変なエラーを表示しないようにする
    exit(0)
  }
  loop {
    begin
      response = manager.get(arrayOID) # MIB値取得
      p '==> response', response if $DEBUG ## DEBUG
      print Time.now.strftime("%Y/%m/%d %H:%M:%S ")
      i = 0
      response.each_varbind do |vb|
        p '==> response.each_varbind', vb if $DEBUG ## DEBUG
        case vb.value.to_s
        when 'noSuchInstance','noSuchObject' then # 正常な値が取れない場合は'-'で表示
          print ",-"
          arrayOld[i] = nil
        else
          # 表示形式によって場合分け mark:区切り文字表示、gauge,gaugef:値をそのまま表示、delta:増分を表示
          case arrayDisp[i]
          when 'mark' then  ## 区切り文字
            print ",#"
          when 'gauge' then ## 絶対値表示
            print ",#{vb.value.to_i}"
          when 'gaugef' then ## 絶対値表示 浮動小数点
            print ",#{vb.value.to_f}"
          when 'gaugef2' then ## 絶対値表示 浮動小数点2桁
            printf(",%.2f", vb.value.to_f)
          when 'delta','bps','pps' then ## 増分表示
            if arrayOld[i] == nil then # 直前の値が取れていない場合は'-'で表示
              print ',^'
            else
              case vb.value.asn1_type # MIB取得した値の種類により分岐。カウンタがラップした時の計算用
              when 'Counter32' then
                wrap_value=4294967296
              when 'Counter64' then
                wrap_value=18446744073709551616
              else
                wrap_value=0
              end

              case arrayDisp[i] # 表示形式によって8倍したり、秒間増加数計算させたり、単純増加数を表示させたりします
              when 'bps' then ## 秒毎の増加数を計算。Octets数からbit数に変換するため8倍します
                bits = 8
                pooling_interval = interval
              when 'pps' then ## 秒毎の増加数を計算
                bits = 1
                pooling_interval = interval
              else ## 単純増加数を出力させる
                bits = 1
                pooling_interval = 1
              end
              
              # bpsやカウンタのラップアラウンドを考慮して出力
              if vb.value.to_i >= arrayOld[i] then
                print ",#{((vb.value.to_i - arrayOld[i]) * bits / pooling_interval).round}"
              else
                print ",#{((vb.value.to_i + (wrap_value - arrayOld[i])) * bits / pooling_interval).round}"
              end
            end
          else # 考慮していない表示形式が来た場合はエラーを吐く、jsonファイルを要確認
            puts "\n==> ERROR:unknown disp value =#{arrayDisp[i]}\n"
          end # case arrayDisp[i] end
          arrayOld[i] = vb.value.to_i # 現在の値を保持する
        end # case vb.value.to_s end
        i += 1
      end # response.each_varbind do end
      puts # 取得し終わったら最後に改行
      sleep interval

    rescue => ex
      # SNMPポーリング等でエラーが発生した場合になんとかする。
      puts Time.now.strftime("%Y/%m/%d %H:%M:%S ,timeout")
      arrayOld = arrayOld.map{|x| nil}
      p '==> Error',ex if $DEBUG ## DEBUG
      sleep interval_rescue
    end
  } # loop end
end

