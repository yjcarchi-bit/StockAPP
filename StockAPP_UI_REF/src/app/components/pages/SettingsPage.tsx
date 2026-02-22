import React from 'react';
import { Settings, Info, Code, Mail } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Label } from '../ui/label';
import { Input } from '../ui/input';
import { Switch } from '../ui/switch';
import { Button } from '../ui/button';

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl mb-2">⚙️ 设置</h1>
        <p className="text-gray-600">系统配置和平台信息</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>系统配置</CardTitle>
          <CardDescription>调整系统默认参数</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <Label>自动保存回测结果</Label>
              <p className="text-sm text-gray-500">回测完成后自动保存结果到本地</p>
            </div>
            <Switch />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <Label>启用数据缓存</Label>
              <p className="text-sm text-gray-500">缓存历史数据以加快回测速度</p>
            </div>
            <Switch defaultChecked />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <Label>显示详细日志</Label>
              <p className="text-sm text-gray-500">在回测过程中显示详细的计算日志</p>
            </div>
            <Switch />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>默认参数</CardTitle>
          <CardDescription>设置回测的默认参数</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label htmlFor="defaultCapital">默认初始资金（元）</Label>
            <Input
              id="defaultCapital"
              type="number"
              defaultValue="100000"
              className="mt-1"
              step="10000"
            />
          </div>

          <div>
            <Label htmlFor="defaultCommission">默认佣金费率（%）</Label>
            <Input
              id="defaultCommission"
              type="number"
              defaultValue="0.03"
              className="mt-1"
              step="0.01"
            />
          </div>

          <div>
            <Label htmlFor="defaultStampDuty">默认印花税率（%）</Label>
            <Input
              id="defaultStampDuty"
              type="number"
              defaultValue="0.1"
              className="mt-1"
              step="0.01"
            />
          </div>

          <Button className="w-full bg-blue-600 hover:bg-blue-700">保存设置</Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Info className="h-5 w-5" />
            <span>关于 StockAPP</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-start space-x-3">
            <Code className="h-5 w-5 text-gray-400 mt-1" />
            <div>
              <div className="font-medium">版本信息</div>
              <p className="text-sm text-gray-600">StockAPP v1.0.0</p>
              <p className="text-sm text-gray-600">最后更新: 2024-02-21</p>
            </div>
          </div>

          <div className="flex items-start space-x-3">
            <Info className="h-5 w-5 text-gray-400 mt-1" />
            <div>
              <div className="font-medium">产品介绍</div>
              <p className="text-sm text-gray-600 mt-1">
                StockAPP 是一款面向 A股投资者的量化策略回测平台，
                帮助用户在历史数据上验证交易策略的有效性，无需编程知识即可进行专业的策略分析。
              </p>
            </div>
          </div>

          <div className="flex items-start space-x-3">
            <Mail className="h-5 w-5 text-gray-400 mt-1" />
            <div>
              <div className="font-medium">联系方式</div>
              <p className="text-sm text-gray-600 mt-1">
                邮箱: support@stockapp.com<br />
                官网: www.stockapp.com
              </p>
            </div>
          </div>

          <div className="pt-4 border-t">
            <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
              <h4 className="font-medium text-yellow-900 mb-2">⚠️ 免责声明</h4>
              <ul className="text-sm text-yellow-800 space-y-1">
                <li>• 本平台仅供学习和研究使用，不构成投资建议</li>
                <li>• 历史回测结果不代表未来表现</li>
                <li>• 投资有风险，入市需谨慎</li>
                <li>• 请根据自身风险承受能力做出投资决策</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>技术栈</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-3 bg-gray-50 rounded text-center">
              <div className="font-medium text-blue-600">React</div>
              <div className="text-xs text-gray-500">前端框架</div>
            </div>
            <div className="p-3 bg-gray-50 rounded text-center">
              <div className="font-medium text-sky-600">Tailwind CSS</div>
              <div className="text-xs text-gray-500">样式框架</div>
            </div>
            <div className="p-3 bg-gray-50 rounded text-center">
              <div className="font-medium text-purple-600">Recharts</div>
              <div className="text-xs text-gray-500">图表库</div>
            </div>
            <div className="p-3 bg-gray-50 rounded text-center">
              <div className="font-medium text-green-600">TypeScript</div>
              <div className="text-xs text-gray-500">类型系统</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
