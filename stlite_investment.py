import pandas as pd
import datetime
from datetime import timedelta
import streamlit as st
import plotly.express as px
import plotly.graph_objs as go

JST = datetime.timezone(timedelta(hours=+9), 'JST')

def get_first_date_of_month(dt):
    return dt.replace(day=1)

def get_first_date_of_year(dt):
    return dt.replace(month=1, day=1)

def get_growth(year, df_buy_hyouka):
    if datetime.date.today().year == year:
        end_date = datetime.date.today()
    else:
        end_date = datetime.date(year=year, month=12, day=31)
    this_year_end_value = df_buy_hyouka['評価額'].loc[end_date.strftime('%Y-%m-%d')]
    previous_year_end_value = df_buy_hyouka['評価額'].loc[datetime.date(year=(year-1), month=12, day=31).strftime('%Y-%m-%d')]
    buy_this_year = df_buy_hyouka['購入額'].loc[end_date.strftime('%Y-%m-%d')] - df_buy_hyouka['購入額'].loc[datetime.date(year=(year-1), month=12, day=31).strftime('%Y-%m-%d')]
    profit = this_year_end_value - buy_this_year - previous_year_end_value
    growth = profit / previous_year_end_value * 100
    this_year_end_value = int(this_year_end_value/10000)
    previous_year_end_value = int(previous_year_end_value/10000)
    buy_this_year = int(buy_this_year/10000)
    profit = int(profit/10000)
    growth = round(growth, 2)
    return this_year_end_value, previous_year_end_value, buy_this_year, profit, growth

@st.cache_data
def load_data():
    # CSVファイルから基準価額データを読み込み
    df_kagaku = pd.read_csv('kagaku_data.csv', index_col=0, parse_dates=True)
    
    # 購入履歴をCSVから読み込み（Excelの代わり）
    buy_xlsx = pd.read_csv('toshin_buy.csv')
    buy_xlsx['年月日'] = pd.to_datetime(buy_xlsx['年月日'])
    
    return df_kagaku, buy_xlsx

def date_judge(date):
    today = datetime.datetime.now() + datetime.timedelta(hours=9)
    delta_days = (today - date).days
    if delta_days == 0:
        return '今日'
    else:
        return (str(delta_days) + '日前')

# メイン処理
st.title('投資履歴ダッシュボード')

# 投資額を設定
kokunai_kongo = 0
senshinkoku_kongo = 0
balance_kongo = 0
zensekai_kongo = 150000
beikoku_kongo = 0

# 年利を設定
dict_growth = {
    "国内株式": 5,
    "先進国株式": 5,
    "全世界株式": 5,
    "米国株式": 5,
    "バランス": 3,
}

# サイドバー
with st.sidebar:
    predict_period = st.slider("予測期間(年)", 0, 30, 0, 1)
    
    senshinkoku_kongo = st.slider("投資額_先進国株式", 0, 40, int(senshinkoku_kongo/10000), 1) * 10000
    zensekai_kongo = st.slider("投資額_全世界株式", 0, 40, int(zensekai_kongo/10000), 1) * 10000
    beikoku_kongo = st.slider("投資額_米国株式", 0, 40, int(beikoku_kongo/10000), 1) * 10000
    kokunai_kongo = st.slider("投資額_国内株式", 0, 40, int(kokunai_kongo/10000), 1) * 10000
    balance_kongo = st.slider("投資額_バランス", 0, 40, int(balance_kongo/10000), 1) * 10000
    
    dict_growth['先進国株式'] = st.slider("年利_先進国株式", 0, 20, dict_growth['先進国株式'], 1)
    dict_growth['全世界株式'] = st.slider("年利_全世界株式", 0, 20, dict_growth['全世界株式'], 1)
    dict_growth['米国株式'] = st.slider("年利_米国株式", 0, 20, dict_growth['米国株式'], 1)
    dict_growth['国内株式'] = st.slider("年利_国内株式", 0, 20, dict_growth['国内株式'], 1)
    dict_growth['バランス'] = st.slider("年利_バランス", 0, 20, dict_growth['バランス'], 1)

try:
    # データ読み込み
    df_kagaku, buy_xlsx = load_data()
    
    str_date = "2017-01-01"
    future_date = str(datetime.date.today() + datetime.timedelta(days=365*predict_period))
    today = datetime.datetime.today()
    
    leatest_date = df_kagaku.index.max()
    
    # 日次データに補完
    date_index = pd.date_range("2017-01-04", end=str(datetime.datetime.today()), freq="D")
    df_new = pd.DataFrame(index=date_index)
    df_new = df_new.rename_axis('日付')
    df_kagaku = pd.merge_asof(df_new, df_kagaku, on='日付', direction='backward')
    df_kagaku = df_kagaku.set_index('日付', drop=True)
    
    # 未来予測データの追加
    df_mirai = pd.DataFrame(index=pd.date_range(df_kagaku.index[len(df_kagaku)-1], future_date, freq='MS'), columns=df_kagaku.columns)
    df_kagaku = pd.concat([df_kagaku, df_mirai]).groupby(level=0).last()
    
    # 未来の基準価額を予測
    for i in range(0, len(df_kagaku)):
        if pd.isna(df_kagaku.iloc[i]['国内株式']) or df_kagaku.iloc[i]['国内株式'] < 0.0:
            for k, v in dict_growth.items():
                df_kagaku.iloc[i, df_kagaku.columns.get_loc(k)] = df_kagaku.iloc[i-1][k] * (1 + v/100) ** (1/365*((df_kagaku.index[i] - df_kagaku.index[i-1]).days))
    
    df_kagaku_hiritu = df_kagaku.copy()
    df_kagaku_hiritu = df_kagaku_hiritu / df_kagaku_hiritu.loc["2017-12-29"] * 100
    
    # 購入履歴の処理
    df_buy = pd.DataFrame()
    for index, data in buy_xlsx.iterrows():
        if data['年月日'] not in df_buy.index or data['アセット'] not in df_buy.columns:
            df_buy.loc[data['年月日'], data['アセット']] = data['価格']
        else:
            df_buy.loc[data['年月日'], data['アセット']] += data['価格']
    
    df_buy = df_buy.rename_axis('年月日')
    
    # 今日以降の積立投資額を変更
    first_row_index = df_buy.reset_index().index[df_buy.index >= today][0] if any(df_buy.index >= today) else len(df_buy)
    
    if first_row_index < len(df_buy):
        df_buy.iloc[first_row_index:, 0] = kokunai_kongo
        df_buy.iloc[first_row_index:, 1] = senshinkoku_kongo
        df_buy.iloc[first_row_index:, 2] = balance_kongo
        df_buy.iloc[first_row_index:, 3] = zensekai_kongo
        df_buy.iloc[first_row_index:, 4] = beikoku_kongo
    
    df_buy = df_buy[(df_buy.index < today) | (df_buy.index.day == 1)]
    
    df_kagaku_hiritu = df_kagaku_hiritu.replace(0, 1.0e-10)
    
    df_kuchisu = (df_buy / df_kagaku_hiritu).fillna(0)
    df_hyouka = df_kagaku_hiritu * df_kuchisu.cumsum()
    
    date_index = df_hyouka.index
    df_new = pd.DataFrame(index=date_index)
    df_new = df_new.rename_axis('日付')
    df_buy2 = pd.concat([df_new, df_buy], axis=1, join='outer')
    
    df_buy_hyouka = pd.concat([df_buy2.fillna(0).cumsum().sum(axis=1), df_hyouka.sum(axis=1)], axis=1)
    df_buy_hyouka.columns = ['購入額', '評価額']
    df_buy_hyouka['税引前利益'] = df_buy_hyouka['評価額'] - df_buy_hyouka['購入額']
    df_buy_hyouka['税引後利益'] = df_buy_hyouka['税引前利益'] * 0.8
    
    # サマリー表示
    display_table = pd.DataFrame({
        '最新基準価額': [leatest_date.strftime('%Y/%m/%d') + ' (' + date_judge(leatest_date) + ')'],
        '評価額': ["{:.2f}".format(int(df_buy_hyouka['評価額'][leatest_date]/10000)/100) + 'M'],
        '総利益': ["{:+.2f}".format(int(df_buy_hyouka['税引前利益'][leatest_date]/10000)/100) + 'M'],
        '年初来': ["{:+.2f}".format(int((df_buy_hyouka['評価額'][leatest_date] - df_buy_hyouka['評価額'][get_first_date_of_year(leatest_date)])/10000)/100) + 'M'],
        '月初来': ["{:+.2f}".format(int((df_buy_hyouka['評価額'][leatest_date] - df_buy_hyouka['評価額'][get_first_date_of_month(leatest_date)])/10000)/100) + 'M'],
        '前日差': ["{:+.2f}".format(int((df_buy_hyouka['評価額'][leatest_date] - df_buy_hyouka['評価額'][leatest_date - datetime.timedelta(days=1)])/10000)/100) + 'M'],
    }).set_index('最新基準価額')
    st.write(display_table)
    
    margin = dict(t=30, b=20, l=20, r=20)
    
    display_month = st.slider("表示する期間(月)", 0, 48, 12, 1)
    str_date2 = datetime.datetime.today() - timedelta(days=display_month*30)
    
    fig4 = px.line(df_buy_hyouka[str_date2:today]['評価額'], title='直近期間')
    fig4.update_layout(margin=margin, width=800, height=400)
    st.plotly_chart(fig4)
    
    df_buy_hyouka = df_buy_hyouka[str_date:future_date]
    df_buy_hyouka = df_buy_hyouka.astype(float)
    
    fig3 = px.line(df_buy_hyouka, title='損益')
    fig3.update_layout(margin=margin, width=800, height=400)
    st.plotly_chart(fig3)
    
    df_hyouka = df_hyouka.astype(float)
    df_hyouka = df_hyouka[str_date:future_date]
    fig2 = px.area(df_hyouka, title='評価額')
    fig2.update_layout(margin=margin, width=800, height=400)
    st.plotly_chart(fig2)
    
    df_kagaku_hiritu = df_kagaku_hiritu.astype(float)
    df_kagaku_hiritu = df_kagaku_hiritu[str_date:future_date]
    fig1 = px.line(df_kagaku_hiritu, title='基準価額推移(2017年末比)')
    fig1.update_layout(margin=margin, width=800, height=400)
    st.plotly_chart(fig1)
    
    # 月次利益グラフ
    monthly_profit = df_buy_hyouka.groupby(pd.Grouper(freq='M'))['税引後利益'].agg('last')
    shifted_monthly_profit = monthly_profit.shift(1)
    monthly_profit_diff = monthly_profit - shifted_monthly_profit
    monthly_profit_diff_df = pd.DataFrame(monthly_profit_diff)
    monthly_profit_diff_df['税引後利益'] = (monthly_profit_diff_df['税引後利益']/10000)
    monthly_profit_diff_df = monthly_profit_diff_df.dropna(subset=['税引後利益'])
    monthly_profit_diff_df['税引後利益'] = monthly_profit_diff_df['税引後利益'].astype(int)
    
    monthly_profit_diff_df["12カ月移動平均"] = monthly_profit_diff_df["税引後利益"].rolling(12).mean()
    monthly_profit_diff_df["24カ月移動平均"] = monthly_profit_diff_df["税引後利益"].rolling(24).mean()
    monthly_profit_diff_df["36カ月移動平均"] = monthly_profit_diff_df["税引後利益"].rolling(36).mean()
    
    trace1 = go.Bar(x=monthly_profit_diff_df.index, y=monthly_profit_diff_df['税引後利益'], text=monthly_profit_diff_df['税引後利益'], name='月次', yaxis='y1', marker_color='#808080')
    trace2 = go.Line(x=monthly_profit_diff_df.index, y=monthly_profit_diff_df['12カ月移動平均'], text=monthly_profit_diff_df['12カ月移動平均'], name='12カ月移動平均', yaxis='y1', line=dict(color="#00008b"))
    trace3 = go.Line(x=monthly_profit_diff_df.index, y=monthly_profit_diff_df['24カ月移動平均'], text=monthly_profit_diff_df['24カ月移動平均'], name='24カ月移動平均', yaxis='y1', line=dict(color="#006400"))
    trace4 = go.Line(x=monthly_profit_diff_df.index, y=monthly_profit_diff_df['36カ月移動平均'], text=monthly_profit_diff_df['36カ月移動平均'], name='36カ月移動平均', yaxis='y1', line=dict(color="#ff0000"))
    
    layout = go.Layout(
        title='月次利益(税引後)',
        xaxis=dict(title='日付', showgrid=False, dtick='M12'),
        yaxis=dict(title='万円', side='left', dtick=50),
    )
    
    fig6 = dict(data=[trace1, trace2, trace3, trace4], layout=layout)
    st.plotly_chart(fig6)
    
    # 年次成長率テーブル
    year_list = []
    this_year_end_value_list = []
    previous_year_end_value_list = []
    buy_this_year_list = []
    profit_list = []
    growth_list = []
    
    all_country_growth_list = []
    advanced_nations_growth_list = []
    sp500_growth_list = []
    japan_growth_list = []
    balance_growth_list = []
    
    for year in range(2018, (datetime.date.today().year + 1)):
        year_list.append(year)
        this_year_end_value, previous_year_end_value, buy_this_year, profit, growth = get_growth(year, df_buy_hyouka)
        this_year_end_value_list.append(this_year_end_value)
        previous_year_end_value_list.append(previous_year_end_value)
        profit_list.append(profit)
        buy_this_year_list.append(buy_this_year)
        growth_list.append(growth)
        
        if datetime.date.today().year == year:
            end_date = datetime.date.today()
        else:
            end_date = datetime.date(year=year, month=12, day=31)
        
        all_country_growth = (df_kagaku['全世界株式'].loc[end_date.strftime('%Y-%m-%d')] - df_kagaku['全世界株式'].loc[datetime.date(year=year-1, month=12, day=31).strftime('%Y-%m-%d')]) / df_kagaku['全世界株式'].loc[datetime.date(year=year-1, month=12, day=31).strftime('%Y-%m-%d')]
        all_country_growth = round(all_country_growth*100, 2)
        all_country_growth_list.append(all_country_growth)
        
        advanced_nations_growth = (df_kagaku['先進国株式'].loc[end_date.strftime('%Y-%m-%d')] - df_kagaku['先進国株式'].loc[datetime.date(year=year-1, month=12, day=31).strftime('%Y-%m-%d')]) / df_kagaku['先進国株式'].loc[datetime.date(year=year-1, month=12, day=31).strftime('%Y-%m-%d')]
        advanced_nations_growth = round(advanced_nations_growth*100, 2)
        advanced_nations_growth_list.append(advanced_nations_growth)
        
        sp500_growth = (df_kagaku['米国株式'].loc[end_date.strftime('%Y-%m-%d')] - df_kagaku['米国株式'].loc[datetime.date(year=year-1, month=12, day=31).strftime('%Y-%m-%d')]) / df_kagaku['米国株式'].loc[datetime.date(year=year-1, month=12, day=31).strftime('%Y-%m-%d')]
        sp500_growth = round(sp500_growth*100, 2)
        sp500_growth_list.append(sp500_growth)
        
        japan_growth = (df_kagaku['国内株式'].loc[end_date.strftime('%Y-%m-%d')] - df_kagaku['国内株式'].loc[datetime.date(year=year-1, month=12, day=31).strftime('%Y-%m-%d')]) / df_kagaku['国内株式'].loc[datetime.date(year=year-1, month=12, day=31).strftime('%Y-%m-%d')]
        japan_growth = round(japan_growth*100, 2)
        japan_growth_list.append(japan_growth)
        
        balance_growth = (df_kagaku['バランス'].loc[end_date.strftime('%Y-%m-%d')] - df_kagaku['バランス'].loc[datetime.date(year=year-1, month=12, day=31).strftime('%Y-%m-%d')]) / df_kagaku['バランス'].loc[datetime.date(year=year-1, month=12, day=31).strftime('%Y-%m-%d')]
        balance_growth = round(balance_growth*100, 2)
        balance_growth_list.append(balance_growth)
    
    growth_df = pd.DataFrame(list(zip(year_list, previous_year_end_value_list, this_year_end_value_list, buy_this_year_list, profit_list, growth_list, advanced_nations_growth_list, all_country_growth_list, japan_growth_list, sp500_growth_list, balance_growth_list)), columns=['年', '年始評価額', '年末評価額', '購入額', '利益', '年利(%)', '先進国年利', '全世界年利', '日経年利', '米国年利', 'バランス年利'])
    growth_df = growth_df.set_index('年')
    st.dataframe(growth_df)

except Exception as e:
    st.error(f"エラーが発生しました: {str(e)}")
    st.info("データファイル(kagaku_data.csv, toshin_buy.csv)が正しく配置されているか確認してください。")
