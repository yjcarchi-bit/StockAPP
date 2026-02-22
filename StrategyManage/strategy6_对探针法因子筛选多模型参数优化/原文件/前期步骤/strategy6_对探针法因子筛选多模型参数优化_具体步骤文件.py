# --------------------------------------------------------------------------------
# 1. 导入库与设置
# --------------------------------------------------------------------------------
from jqdata import *
from jqlib.technical_analysis import *
from jqfactor import get_factor_values, winsorize_med, standardlize, neutralize
import datetime
import pandas as pd
import numpy as np
from scipy import stats
import statsmodels.api as sm
from sklearn.decomposition import PCA
from sklearn import svm
from sklearn.model_selection import train_test_split
from sklearn.metrics import (accuracy_score, precision_score, recall_score, 
                             f1_score, roc_auc_score, confusion_matrix, 
                             roc_curve, precision_recall_curve, auc, 
                             mean_squared_error, mean_absolute_error)
from tqdm import tqdm
import matplotlib.pyplot as plt
import seaborn as sns
import pickle
import lightgbm as lgb
import warnings
warnings.filterwarnings("ignore")

# --------------------------------------------------------------------------------
# 2. 因子列表定义
# --------------------------------------------------------------------------------
jqfactors_list=['DAVOL5', 'interest_free_current_liability', 'sales_to_price_ratio', 
                'cash_flow_to_price_ratio', 'VOSC', 'momentum', 'Kurtosis60', 
                'Kurtosis20', 'Kurtosis120', 'Skewness60', 'Skewness20', 'MAWVAD', 
                'turnover_volatility', 'Variance20', 'MASS', 'VMACD', 'ATR6', 'MFI14', 
                'CR20', 'leverage', 'ATR14', 'money_flow_20', 'earnings_yield', 
                'circulating_market_cap', 'book_to_price_ratio', 'natural_log_of_market_cap', 
                'cube_of_size', 'financial_assets', 'VEMA5', 'PSY', 
                'daily_standard_deviation', 'single_day_VPT_12', 'single_day_VPT', 
                'ROC120', 'BIAS60', 'price_no_fq', 'arron_down_25', 'arron_up_25', 
                'Rank1M', 'fifty_two_week_close_rank', 'bear_power', 'liquidity', 
                'WVAD', 'VDIFF']

# --------------------------------------------------------------------------------
# 3. 数据获取与处理函数
# --------------------------------------------------------------------------------
def get_period_date(period, start_date, end_date):
    stock_data = get_price('000001.XSHE', start_date, end_date, 'daily', fields=['close'])
    period_stock_data = stock_data.resample(period).last().dropna()
    date_list = period_stock_data.index.strftime('%Y-%m-%d').tolist()
    adjusted_start = (pd.to_datetime(start_date) - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
    date_list.insert(0, adjusted_start)
    return date_list

def delect_stop(stocks, beginDate, n=30 * 3):
    stockList = []
    beginDate = datetime.datetime.strptime(beginDate, "%Y-%m-%d")
    for stock in stocks:
        start_date = get_security_info(stock).start_date
        if start_date < (beginDate - datetime.timedelta(days=n)).date():
            stockList.append(stock)
    return stockList

def get_stock(stockPool, begin_date):
    if stockPool == 'AA':
        stockList = get_index_stocks('000985.XSHG', begin_date)
        stockList = [stock for stock in stockList if not stock.startswith(('3', '68', '4', '8'))]
    
    st_data = get_extras('is_st', stockList, count=1, end_date=begin_date)
    stockList = [stock for stock in stockList if not st_data[stock][0]]
    stockList = delect_stop(stockList, begin_date)
    return stockList

def get_factor_data(securities_list, date):
    factor_data = get_factor_values(securities=securities_list, factors=jqfactors_list, count=1, end_date=date)
    df_jq_factor = pd.DataFrame(index=securities_list)
    for i in factor_data.keys():
        df_jq_factor[i] = factor_data[i].iloc[0, :]
    return df_jq_factor

# --------------------------------------------------------------------------------
# 4. 执行数据下载 (初次运行需执行，之后可读取csv)
# --------------------------------------------------------------------------------
period = '2M' # 可以根据需要修改周期，原文是2M
start_date = '2015-01-01'
end_date = '2024-01-01'
dateList = get_period_date(period, start_date, end_date)

DF = pd.DataFrame()
for i, trade_date in enumerate(tqdm(dateList[:-1], desc='downloading')):
    stockList = get_stock('AA', trade_date)
    if not stockList: continue
    factor_origl_data = get_factor_data(stockList, trade_date)
    next_date = dateList[i + 1]
    px = get_price(stockList, trade_date, next_date, '1d', 'close')['close']
    # 计算收益率
    factor_origl_data['pchg'] = px.iloc[-1] / px.iloc[0] - 1
    factor_origl_data['trade_date'] = trade_date
    factor_origl_data = factor_origl_data.dropna()
    DF = pd.concat([DF, factor_origl_data], ignore_index=True)
DF.to_csv(r'train.csv', index=False)

# --------------------------------------------------------------------------------
# 5. 模型训练与特征筛选 (核心逻辑)
# --------------------------------------------------------------------------------
# 加载数据
df = pd.read_csv('train.csv')

# 标签构造
df['label_class'] = (df['pchg'] > df.groupby('trade_date')['pchg'].transform('median')).astype(int)
df['label_res'] = df.groupby('trade_date')['pchg'].transform(
    lambda s: (s.rank(method='first', ascending=True) - 1) / (len(s) - 1) if len(s) > 1 else 0.5
)
df['label_dir'] = (df['pchg'] > 0).astype(int)

df['trade_date'] = pd.to_datetime(df['trade_date'])

# 数据切分
exclude_cols = ['trade_date', 'pchg', 'label_class', 'label_res', 'label_dir']
feature_names = [col for col in df.columns if col not in exclude_cols]

train_df = df[df['trade_date'].dt.year < 2023].copy()
test_df  = df[df['trade_date'].dt.year >= 2023].copy()

train_df = train_df.sort_values('trade_date')
split_point = int(len(train_df) * 0.9)
train_idx = train_df.index[:split_point]
val_idx   = train_df.index[split_point:]

# LGBM 参数
params_cls = {'objective': 'binary', 'metric': 'auc', 'seed': 42, 'verbose': -1}
params_dir = {'objective': 'binary', 'metric': 'auc', 'seed': 42, 'verbose': -1}
params_reg = {'objective': 'regression', 'metric': 'rmse', 'seed': 42, 'verbose': -1}

# === 增强探针法因子筛选 ===
print("开始增强探针法因子筛选...")
N_ITER = 10
N_NOISE = 10
current_features = feature_names.copy()

y_train_cls = df.loc[train_idx, 'label_class'].values
y_val_cls = df.loc[val_idx, 'label_class'].values
y_train_reg = df.loc[train_idx, 'label_res'].values
y_val_reg = df.loc[val_idx, 'label_res'].values
y_train_dir = df.loc[train_idx, 'label_dir'].values
y_val_dir = df.loc[val_idx, 'label_dir'].values

for iter_idx in range(1, N_ITER + 1):
    X_train_curr = df.loc[train_idx, current_features].values.astype('float32')
    X_val_curr   = df.loc[val_idx, current_features].values.astype('float32')
    
    # 生成噪音
    noise_train = np.random.randn(X_train_curr.shape[0], N_NOISE).astype('float32')
    noise_val   = np.random.randn(X_val_curr.shape[0], N_NOISE).astype('float32')
    
    X_train_aug = np.hstack([X_train_curr, noise_train])
    X_val_aug   = np.hstack([X_val_curr, noise_val])
    
    # 训练三个模型
    lgb_train_cls = lgb.Dataset(X_train_aug, y_train_cls)
    lgb_val_cls   = lgb.Dataset(X_val_aug, y_val_cls, reference=lgb_train_cls)
    model_cls = lgb.train(params_cls, lgb_train_cls, valid_sets=[lgb_val_cls], early_stopping_rounds=20, verbose_eval=False)
    
    lgb_train_reg = lgb.Dataset(X_train_aug, y_train_reg)
    lgb_val_reg   = lgb.Dataset(X_val_aug, y_val_reg, reference=lgb_train_reg)
    model_reg = lgb.train(params_reg, lgb_train_reg, valid_sets=[lgb_val_reg], early_stopping_rounds=20, verbose_eval=False)
    
    lgb_train_dir = lgb.Dataset(X_train_aug, y_train_dir)
    lgb_val_dir   = lgb.Dataset(X_val_aug, y_val_dir, reference=lgb_train_dir)
    model_dir = lgb.train(params_dir, lgb_train_dir, valid_sets=[lgb_val_dir], early_stopping_rounds=20, verbose_eval=False)

    # 获取重要性
    imp_cls = model_cls.feature_importance(importance_type='gain')
    imp_reg = model_reg.feature_importance(importance_type='gain')
    imp_dir = model_dir.feature_importance(importance_type='gain')
    
    # 噪音阈值
    noise_imp_cls_max = np.max(imp_cls[-N_NOISE:])
    noise_imp_reg_max = np.max(imp_reg[-N_NOISE:])
    noise_imp_dir_max = np.max(imp_dir[-N_NOISE:])
    
    to_remove = []
    for idx, feat in enumerate(current_features):
        if (imp_cls[idx] < noise_imp_cls_max) and (imp_reg[idx] < noise_imp_reg_max) and (imp_dir[idx] < noise_imp_dir_max):
            to_remove.append(feat)
    
    current_features = [f for f in current_features if f not in to_remove]
    print(f"轮次 {iter_idx}: 剩余特征 {len(current_features)}")

# 保存筛选后的特征
df_selected_factors = pd.DataFrame(current_features, columns=['factor'])
df_selected_factors.to_csv('selected_factors.csv', index=False)

# === 最终模型训练 ===
print("训练最终模型...")
X_train_final = df.loc[train_idx, current_features].values.astype('float32')
X_val_final   = df.loc[val_idx, current_features].values.astype('float32')

lgb_train_cls_final = lgb.Dataset(X_train_final, y_train_cls)
lgb_val_cls_final   = lgb.Dataset(X_val_final, y_val_cls, reference=lgb_train_cls_final)
model_cls_final = lgb.train(params_cls, lgb_train_cls_final, valid_sets=[lgb_val_cls_final], num_boost_round=1000, early_stopping_rounds=50, verbose_eval=False)

lgb_train_reg_final = lgb.Dataset(X_train_final, y_train_reg)
lgb_val_reg_final   = lgb.Dataset(X_val_final, y_val_reg, reference=lgb_train_reg_final)
model_reg_final = lgb.train(params_reg, lgb_train_reg_final, valid_sets=[lgb_val_reg_final], num_boost_round=1000, early_stopping_rounds=50, verbose_eval=False)

lgb_train_dir_final = lgb.Dataset(X_train_final, y_train_dir)
lgb_val_dir_final   = lgb.Dataset(X_val_final, y_val_dir, reference=lgb_train_dir_final)
model_dir_final = lgb.train(params_dir, lgb_train_dir_final, valid_sets=[lgb_val_dir_final], num_boost_round=1000, early_stopping_rounds=50, verbose_eval=False)

# 保存模型
with open('model_cls_final.pkl', 'wb') as f:
    pickle.dump(model_cls_final, f)
with open('model_reg_final.pkl', 'wb') as f:
    pickle.dump(model_reg_final, f)
with open('model_dir_final.pkl', 'wb') as f:
    pickle.dump(model_dir_final, f)

print("训练与保存完成！")