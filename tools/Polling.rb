#!/usr/bin/ruby -Ks
ScriptDescription="MIB Polling Script By masayuki.azuma@gmail.com"
Version="2019.07.29"
#
# 更新履歴等
# 2015/07/07 とりあえず作った
# 2015/07/09 SNMPGet timeout時の例外処理追加
# 2015/08/20 BPS,PPS計算を追加。これに伴いcsvヘッダにdescriptionだけでなくdisp形式も記載するようにした
# 2016/01/18 CPU Loadのように小数点以下の値を持つ場合に小数点以下がto_iで切り捨てされてしまったのでto_fにするgaugefを追加した
# 2016/11/02 小数点の桁数を合わせるため、gaugef2を追加した
# 2019/04/22 変数名等の整理等
# 2019/06/28 thread処理に対応。snmp応答遅延時の遅延が緩和されたはず
# 2019/07/09 MIB定義ファイルとしてYAMLフォーマットに対応
# 2019/07/29 snmp_retriesの初期値を0に変更

require 'rubygems'
require 'optparse'
require 'json'
require 'yaml'
require 'snmp'

# オプション指定しない場合のデフォルトパラメータ設定
community    = 'public'
mdatafile    = '/ocn-gin/script/Polling/mib-Sample.json'
target_ip    = '127.0.0.1'
target_port  = 161
interval     = 10
snmp_timeout = 1    # SNMP getのタイムアウト時間(秒)

# その他パラメータ
snmp_retries = 0    # SNMP getタイムアウト時の再試行回数

# コマンドラインオプションの読み込み
opt = OptionParser.new
OPTS = {}
opt.banner="Usage: Polling.rb [options]"
opt.on("-c [community]"         , desc="# default = #{community}")      {|v| OPTS[:c] = v}
opt.on("-m [mib.json|mib.yaml]" , desc="# default = #{mdatafile}")      {|v| OPTS[:m] = v}
opt.on("-t [terget_ip]"         , desc="# default = #{target_ip}")      {|v| OPTS[:t] = v}
opt.on("-p [terget_port]"       , desc="# default = #{target_port}")    {|v| OPTS[:p] = v}
opt.on("-i [interval]"          , desc="# default = #{interval}")       {|v| OPTS[:i] = v}
opt.on("-o [snmp_timeout]"      , desc="# default = #{snmp_timeout}")   {|v| OPTS[:o] = v}
opt.on("-r [snmp_retries]"      , desc="# default = #{snmp_retries}")   {|v| OPTS[:r] = v}
opt.on("-d"                     , desc="# DEBUG ENABLE")                {|v| OPTS[:d] = v}
opt.on_tail("\n#{ScriptDescription}\nVersion: #{Version}")
opt.parse!(ARGV)

if OPTS[:c] then community    = OPTS[:c]      end
if OPTS[:m] then mdatafile    = OPTS[:m]      end
if OPTS[:t] then target_ip    = OPTS[:t]      end
if OPTS[:p] then target_port  = OPTS[:p].to_i end
if OPTS[:i] then interval     = OPTS[:i].to_i end
if OPTS[:o] then snmp_timeout = OPTS[:o].to_i end
if OPTS[:r] then snmp_retries = OPTS[:r].to_i end
if OPTS[:d] then $DEBUG       = true          end

# MIB取得間隔は最低でも1sec
if interval < 1 then interval = 1 end

# バッファせずに即時出力。リダイレクト等の際に効いてくる
STDOUT.sync = true

# スクリプト起動時オプションを出力
print "##SNMP Polling:target_ip=\"#{target_ip}\" target_port=\"#{target_port}\" mdata=\"#{mdatafile}\" community=\"#{community}\" interval=#{interval} snmp_timeout=#{snmp_timeout} snmp_retries=#{snmp_retries}\n"

# ポーリング対象MIB情報をJSONまたはYAMLファイルから読み込む。ファイル形式は拡張子で判定。
case File.extname(mdatafile)
when '.json'
  data = open(mdatafile) do |io|
    JSON.load(io)
  end
when '.yaml','.yml'
  data = open(mdatafile) do |io|
    YAML.load(io)
  end
else
  puts "unknown mib file #{mdatafile}"
  exit
end
p '==> MIB', data if $DEBUG ## DEBUG

# MIB情報ファイルからポーリングOID等を読み込みつつCSVヘッダ表示。多次元配列的にするべきではある
arrayDescr = Array.new # 表示カウンタ名
arrayDisp  = Array.new # 表示形式
arrayOID   = Array.new # SNMP Pollingする対象OID
arrayOld   = Array.new # 取得したMIBカウンタ実測値
print "#time"
if data['miblist'] then
  data['miblist'].each do |obj|
    print ',', obj["description"]
    print ':', obj["disp"]
    arrayDescr.push(obj["description"])
    arrayDisp.push(obj["disp"])
    arrayOID.push(obj["oid"])
    arrayOld.push(nil)  # initialize
  end
end

# ヘッダ表示後の改行
puts

def snmpget(manager,interval,arrayOID,arrayDisp,arrayOld)
  begin
    line = "" # 出力用文字列
    line << Time.now.strftime("%Y/%m/%d %H:%M:%S ")
    response = manager.get(arrayOID) # MIB値取得
    p '==> response', response if $DEBUG ## DEBUG
    # 取得結果それぞれの計算
    i = 0
    response.each_varbind do |vb|
      p '==> response.each_varbind', vb if $DEBUG ## DEBUG
      case vb.value.to_s
      when 'noSuchInstance','noSuchObject' then # 正常な値が取れない場合は'-'で表示
        line << ",-"
        arrayOld[i] = nil
      else
        # 表示形式によって場合分け mark:区切り文字表示、gauge,gaugef:値をそのまま表示、delta:増分を表示
        case arrayDisp[i]
        when 'mark' then  ## 区切り文字
          line << ",#"
        when 'gauge' then ## 絶対値表示
          line << ",#{vb.value.to_i}"
        when 'gaugef' then ## 絶対値表示 浮動小数点
          line << ",#{vb.value.to_f}"
        when 'gaugef2' then ## 絶対値表示 浮動小数点2桁
          line << ",%#.02g" % vb.value.to_f
        when 'delta','bps','pps' then ## 増分表示
          if arrayOld[i] == nil then # 直前の値が取れていない場合は'^'で表示
            line << ',^'
          else # 直前の値が存在する場合は差分を計算する
            # MIB取得した値の種類により分岐。カウンタがラップした時の計算用
            case vb.value.asn1_type
            when 'Counter32' then
              wrap_value=4294967296
            when 'Counter64' then
              wrap_value=18446744073709551616
            else
              wrap_value=0
            end

            # 表示形式によって8倍したり、秒間増加数計算させたり、単純増加数を表示させたりします
            case arrayDisp[i]
            when 'bps' then ## 秒毎の増加数を計算。Octets数からbit数に変換するため8倍します
              bits = 8
              polling_interval = interval
            when 'pps' then ## 秒毎の増加数を計算
              bits = 1
              polling_interval = interval
            else ## 単純増加数を出力させる
              bits = 1
              polling_interval = 1
            end

            # bpsやカウンタのラップアラウンドを考慮して出力
            if vb.value.to_i >= arrayOld[i] then
              line << ",#{((vb.value.to_i - arrayOld[i]) * bits / polling_interval).round}"
            else
              line << ",#{((vb.value.to_i + (wrap_value - arrayOld[i])) * bits / polling_interval).round}"
            end
          end
        else # 考慮していない表示形式が来た場合はエラーを吐く、MIB定義ファイルを要確認
          puts "\n==> ERROR:unknown disp value =#{arrayDisp[i]}\n"
        end # case arrayDisp[i] end
        arrayOld[i] = vb.value.to_i # 最新の値を保持する
      end # case vb.value.to_s end
      i += 1
    end # response.each_varbind do end
    puts line # 全要素の処理が終わったら最後に改行

  rescue => ex
    # SNMPポーリング等でエラーが発生した場合、タイムアウト表示を行い、差分計算用データを初期化する
    line << ',timeout'
    puts line
    # puts Time.now.strftime("%Y/%m/%d %H:%M:%S ,timeout")
    arrayOld = arrayOld.map{|x| nil}
    p '==> Error',ex if $DEBUG ## DEBUG
  end
end

# SNMPポーリング実施
SNMP::Manager.open(:host => target_ip, :port => target_port, :community => community, :timeout => snmp_timeout, :retries => snmp_retries) do |manager|
  Signal.trap(:INT){ # Ctrl+Cで終了されたときに変なエラーを表示しないようにする
    exit(0)
  }
  loop {
    threads = []
    threads << Thread.new { sleep(interval) }
    threads << Thread.fork { snmpget(manager,interval,arrayOID,arrayDisp,arrayOld) }
    threads.each { |thread| thread.join }
  } # loop end
end
